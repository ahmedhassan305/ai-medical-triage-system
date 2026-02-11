from fastapi import APIRouter

from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_service import run_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
def triage(payload: TriageRequest) -> TriageResponse:
    return run_triage(payload)
