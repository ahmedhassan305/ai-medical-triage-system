from fastapi import APIRouter

from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_service import triage as run_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
def triage_route(payload: TriageRequest) -> TriageResponse:
    return run_triage(payload.query)
