from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.db.models import TriageAssessment, User
from app.db.session import get_db
from app.schemas.triage import (
    TriageAssessmentResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.access_control import ensure_patient_profile_access
from app.services.clinical_records import persist_triage_assessment
from app.services.triage_service import triage as run_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    payload: TriageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> TriageResponse:
    patient = None
    if payload.patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to use patient context.",
            )
        patient = ensure_patient_profile_access(db, current_user, payload.patient_id)

    response = run_triage(
        payload.query,
        patient_id=patient.id if patient else None,
        db=db,
    )
    if patient is not None:
        persist_triage_assessment(
            db,
            patient=patient,
            query_text=payload.query,
            response=response,
        )
        db.commit()
    return response


@router.get(
    "/triage/history/{patient_id}", response_model=list[TriageAssessmentResponse]
)
def triage_history_route(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TriageAssessmentResponse]:
    ensure_patient_profile_access(db, current_user, patient_id)
    return (
        db.query(TriageAssessment)
        .filter(TriageAssessment.patient_id == patient_id)
        .order_by(TriageAssessment.created_at.desc())
        .all()
    )
