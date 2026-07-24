import logging
import re
import time
from typing import Dict, Any, List

from ocr_engine import ocr_engine

logger = logging.getLogger(__name__)


class PaddleService:
    def perform_ocr(self, filepath: str) -> Dict[str, Any]:
        start_time = time.perf_counter()
        result = ocr_engine.run_ocr(filepath)
        ocr_time = round(time.perf_counter() - start_time, 3)

        raw_text = result.get("raw_text", "")
        lines = result.get("lines", [])
        cleaned_text = self._clean_ocr_text(lines)

        return {
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "lines": lines,
            "ocr_time": ocr_time,
        }

    @staticmethod
    def _clean_ocr_text(lines: List[Dict[str, Any]]) -> str:
        cleaned_lines = []
        for line in lines:
            text = str(line.get("text", ""))
            normalized = text.replace("\r", "\n")
            normalized = re.sub(r"\s+", " ", normalized).strip()
            if normalized:
                cleaned_lines.append(normalized)

        return "\n".join(cleaned_lines)
