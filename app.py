import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
import uuid
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from paddleocr import PaddleOCR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PaddleOCR Service")

# Initialize PaddleOCR
# use_angle_cls=True to automatically classify text angle
# lang='en' for English, can be modified as needed
try:
    logger.info("Initializing PaddleOCR engine...")
    ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    logger.info("PaddleOCR engine initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize PaddleOCR: {e}")
    ocr = None

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/ocr")
async def perform_ocr(file: UploadFile = File(...)):
    if not ocr:
        raise HTTPException(status_code=500, detail="OCR engine is not initialized.")
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    file_extension = file.filename.split(".")[-1] if "." in file.filename else "img"
    temp_filename = f"{uuid.uuid4()}.{file_extension}"
    temp_filepath = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        # Save uploaded image temporarily
        with open(temp_filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Perform OCR
        logger.info(f"Processing image: {temp_filename}")
        result_list = list(ocr.predict(temp_filepath))
        
        lines = []
        if result_list and len(result_list) > 0:
            res_dict = result_list[0]
            rec_texts = res_dict.get('rec_texts', [])
            rec_scores = res_dict.get('rec_scores', [])
            dt_polys = res_dict.get('dt_polys', [])
            
            for i in range(len(rec_texts)):
                box = dt_polys[i] if i < len(dt_polys) else []
                if hasattr(box, 'tolist'):
                    box = box.tolist()
                lines.append({
                    "text": str(rec_texts[i]),
                    "confidence": float(rec_scores[i]),
                    "boundingBox": box
                })
        
        return {
            "success": True,
            "text": " ".join([line["text"] for line in lines]),
            "lines": lines
        }

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )
    finally:
        # Delete temporary image
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            logger.info(f"Cleaned up temporary file: {temp_filepath}")
