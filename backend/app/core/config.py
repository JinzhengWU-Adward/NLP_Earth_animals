from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    project_name: str = "GeoBioMap API"
    data_path: Path = Path(__file__).resolve().parents[3] / "data" / "species.json"
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # DeepSeek (OpenAI-compatible) Chat Completions
    deepseek_api_key: str | None = Field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    deepseek_base_url: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    deepseek_model: str = Field(default_factory=lambda: os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))
    deepseek_timeout_s: float = Field(default_factory=lambda: float(os.getenv("DEEPSEEK_TIMEOUT_S", "30")))
    deepseek_max_tokens: int = Field(default_factory=lambda: int(os.getenv("DEEPSEEK_MAX_TOKENS", "700")))


settings = Settings()

