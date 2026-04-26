from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_v1_router, legacy_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import add_request_logging_middleware
from app.db.session import create_all
from app.services.triage_service import get_reasoner


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    if (
        settings.app_env != "development"
        and settings.jwt_secret_key == "change-me-in-production"
    ):
        raise RuntimeError("JWT_SECRET_KEY must be set to a non-default value.")

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

    return app


app = create_app()
