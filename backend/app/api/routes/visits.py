from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import PatientProfile, User, Visit
from app.db.session import get_db
from app.schemas.visit import VisitCreate, VisitResponse

router = APIRouter(prefix="/visits", tags=["visits"])


@router.post("/", response_model=VisitResponse)
def create_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> VisitResponse:
    patient = (
        db.query(PatientProfile).filter(PatientProfile.id == payload.patient_id).first()
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    visit = Visit(**payload.model_dump())
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return VisitResponse.model_validate(visit, from_attributes=True)


@router.get("/patient/{patient_id}", response_model=list[VisitResponse])
def list_patient_visits(
    patient_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[VisitResponse]:
    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient_id)
        .order_by(Visit.created_at.desc())
        .all()
    )
    return [VisitResponse.model_validate(item, from_attributes=True) for item in visits]
