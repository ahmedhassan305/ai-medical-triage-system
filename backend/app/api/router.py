from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.triage import router as triage_router
from app.core.config import get_settings

settings = get_settings()

api_v1_router = APIRouter(prefix=settings.api_v1_prefix)
api_v1_router.include_router(health_router)
api_v1_router.include_router(triage_router)

legacy_router = APIRouter()
legacy_router.include_router(health_router)
legacy_router.include_router(triage_router)
