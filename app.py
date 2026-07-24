import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import logging
from fastapi import FastAPI

from config import settings
from routes.ocr import router as ocr_router
from services.slm_service import SLMService

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title="PaddleOCR Service")
app.include_router(ocr_router)

slm_service = SLMService()

@app.on_event("startup")
async def validate_gpt_endpoint():
    await slm_service.validate_endpoint()
