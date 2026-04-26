from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.model.reasoner import OllamaReasoner

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready() -> dict[str, object]:
    settings = get_settings()
    db_ok = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    ollama_ok = True
    if settings.reasoner_mode == "ollama":
        ollama_ok = OllamaReasoner(
            host=settings.ollama_host,
            model=settings.ollama_model,
        ).ping()

    payload = {
        "status": "ok" if db_ok and ollama_ok else "degraded",
        "database": db_ok,
        "ollama": ollama_ok,
    }
    if db_ok and ollama_ok:
        return payload
    return JSONResponse(status_code=503, content=payload)
