from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_service import triage as run_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    payload: TriageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> TriageResponse:
    if payload.patient_id is not None and current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return run_triage(
        payload.query,
        patient_id=payload.patient_id,
        db=db,
    )
