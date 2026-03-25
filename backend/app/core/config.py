from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    project_name: str = "GeoBioMap API"
    data_path: Path = Path(__file__).resolve().parents[3] / "data" / "species.json"
    cors_allow_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()

