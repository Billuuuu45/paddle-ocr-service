import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts" / "ocr_prompt.txt"


class PromptService:
    def __init__(self, prompt_path: Optional[Path] = None):
        self.prompt_path = prompt_path or PROMPT_FILE
        self.prompt_template = self.load_prompt_template()

    def load_prompt_template(self) -> str:
        with open(self.prompt_path, "r", encoding="utf-8") as prompt_file:
            template = prompt_file.read().strip()
        logger.info("Loaded OCR prompt template from %s", self.prompt_path)
        return template

    def build_prompt(self, ocr_text: str) -> str:
        prompt = f"{self.prompt_template}\n\nOCR Text:\n{ocr_text.strip()}"
        logger.info("Generated prompt for GPT request.")
        return prompt
