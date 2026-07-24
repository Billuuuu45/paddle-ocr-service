from PIL.Image import logger
import os
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"

import logging
from paddleocr import PaddleOCR

class OCREngine:
    def __init__(self):
        try:
            logger.info("Initializing PaddleOCR engine...")
            self.ocr = PaddleOCR(use_textline_orientation=True, lang='en')
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR: {e}")
            self.ocr = None

    def run_ocr(self, filepath: str) -> dict:
        if not self.ocr:
            raise RuntimeError("OCR engine is not initialized.")
            
        logger.info(f"Processing file with PaddleOCR: {filepath}")
        result_list = list(self.ocr.predict(filepath))
        
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
                
        raw_text = " ".join([line["text"] for line in lines])
        
        return {
            "raw_text": raw_text,
            "lines": lines
        }

# Singleton instance
ocr_engine = OCREngine()
