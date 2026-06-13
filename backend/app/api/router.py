from fastapi import APIRouter

from app.api.routes.appointments import router as appointments_router
from app.api.routes.auth import router as auth_router
from app.api.routes.clarify import router as clarify_router
from app.api.routes.doctors import router as doctors_router
from app.api.routes.health import router as health_router
from app.api.routes.patients import router as patients_router
from app.api.routes.records_import import router as records_router
from app.api.routes.triage import router as triage_router
from app.api.routes.visits import router as visits_router
from app.core.config import get_settings

settings = get_settings()

api_v1_router = APIRouter(prefix=settings.api_v1_prefix)
api_v1_router.include_router(health_router)
api_v1_router.include_router(triage_router)
api_v1_router.include_router(clarify_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(patients_router)
api_v1_router.include_router(doctors_router)
api_v1_router.include_router(visits_router)
api_v1_router.include_router(appointments_router)
api_v1_router.include_router(records_router)

legacy_router = APIRouter()
legacy_router.include_router(health_router)
legacy_router.include_router(triage_router)
