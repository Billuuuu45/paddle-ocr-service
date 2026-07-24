import logging
import os
import time
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from config import settings
from extractor import extract_structured_invoice_data
from models import StructuredAPIResponse
from services.slm_service import (
    GPTAPIError,
    GPTConnectionError,
    GPTTimeoutError,
    InvalidJSONResponseError,
    SLMService,
)
from services.paddle_service import PaddleService
from services.prompt_service import PromptService

logger = logging.getLogger(__name__)
router = APIRouter()

paddle_service = PaddleService()
prompt_service = PromptService()
slm_service = SLMService()


@router.get("/", response_class=HTMLResponse)
async def serve_ui():
    with open("index.html", "r", encoding="utf-8") as ui_file:
        return ui_file.read()


@router.post("/ocr", response_model=StructuredAPIResponse)
async def perform_ocr(file: UploadFile = File(...)):
    if not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image or PDF.")

    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    file_extension = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "img"
    temp_filename = f"{uuid.uuid4()}.{file_extension}"
    temp_filepath = os.path.join(upload_dir, temp_filename)

    try:
        with open(temp_filepath, "wb") as temp_file:
            temp_file.write(await file.read())

        ocr_result = paddle_service.perform_ocr(temp_filepath)
        logger.info("Uploaded file=%s OCR time=%.3fs", file.filename, ocr_result["ocr_time"])
        logger.debug("Raw OCR text: %s", ocr_result["raw_text"])

        if not ocr_result["cleaned_text"].strip():
            raise HTTPException(status_code=422, detail="OCR extraction produced no text. The uploaded image may be empty or unreadable.")

        prompt = prompt_service.build_prompt(ocr_result["cleaned_text"])
        logger.debug("Prompt sent to GPT: %s", prompt)

        try:
            structured_response = await slm_service.generate_structured_json(prompt)
            document_type = structured_response.get("document_type", "unknown")
            structured_data = structured_response.get("structured_data", {})
        except (GPTTimeoutError, GPTConnectionError, GPTAPIError, InvalidJSONResponseError) as exc:
            logger.warning("SLM unavailable, falling back to local structured extraction: %s", exc)
            structured_data = extract_structured_invoice_data(ocr_result["raw_text"], ocr_result["lines"])
            document_type = "unknown"

        response_payload = {
            "success": True,
            "document_type": document_type,
            "structured_data": structured_data,
            "raw_text": ocr_result["raw_text"],
        }

        return JSONResponse(status_code=200, content=response_payload)
    except HTTPException:
        raise
    except (GPTTimeoutError, GPTConnectionError, GPTAPIError, InvalidJSONResponseError) as exc:
        logger.error("SLM post-processing failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"GPT post-processing failed: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error during OCR processing.")
        raise HTTPException(status_code=500, detail="Internal server error during OCR processing.")
    finally:
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            logger.info("Removed temporary file: %s", temp_filepath)
