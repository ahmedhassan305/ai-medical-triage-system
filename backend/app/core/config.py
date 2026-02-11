from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]


def get_settings() -> Settings:
    origins = _split_csv(os.getenv("CORS_ORIGINS"))
    if not origins:
        raise RuntimeError("CORS_ORIGINS is required. Set it in backend/.env")
    return Settings(cors_origins=origins)
