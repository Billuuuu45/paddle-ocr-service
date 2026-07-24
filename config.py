from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gpt_endpoint: str = Field(
        "https://openrouter.ai/api/v1/chat/completions",
        env="GPT_ENDPOINT",
    )
    gpt_payload_type: str = Field("chat", env="GPT_PAYLOAD_TYPE")
    gpt_model: str = Field("GPT-OSS-20B", env="GPT_MODEL")
    gpt_temperature: float = Field(0.0, env="GPT_TEMPERATURE")
    gpt_max_tokens: int = Field(1024, env="GPT_MAX_TOKENS")
    gpt_timeout: int = Field(30, env="GPT_TIMEOUT")
    gpt_api_key: Optional[str] = Field(None, env="GPT_API_KEY")
    include_raw_ocr_text: bool = Field(False, env="INCLUDE_RAW_OCR_TEXT")
    upload_dir: str = Field("uploads", env="UPLOAD_DIR")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
