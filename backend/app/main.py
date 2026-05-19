import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router, legacy_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import add_request_logging_middleware
from app.db.session import create_all
from app.services.triage_service import _preload_model, get_reasoner


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_request_logging_middleware(app)
    register_exception_handlers(app)

    app.include_router(api_v1_router)
    app.include_router(legacy_router, include_in_schema=False)

    if settings.db_auto_create:
        create_all()

    if settings.strict_reasoner:
        get_reasoner()
    if settings.reasoner_mode == "ollama" and "PYTEST_CURRENT_TEST" not in os.environ:
        # Keep local Ollama warm without leaving noisy background threads in tests.
        threading.Thread(target=_preload_model, daemon=True).start()

    return app


app = create_app()
