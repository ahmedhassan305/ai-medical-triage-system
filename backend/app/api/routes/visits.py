from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import User, Visit
from app.db.session import get_db
from app.schemas.visit import VisitCreate, VisitResponse
from app.services.access_control import (
    ensure_patient_profile_access,
    get_linked_doctor_profile,
    get_patient_profile_or_404,
)

router = APIRouter(prefix="/visits", tags=["visits"])


@router.post("/", response_model=VisitResponse)
def create_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> VisitResponse:
    get_patient_profile_or_404(db, payload.patient_id)
    visit_data = payload.model_dump()
    if current_user.role == "doctor":
        doctor_profile = get_linked_doctor_profile(db, current_user)
        if doctor_profile is None:
            raise HTTPException(
                status_code=403,
                detail="Doctor profile is required before creating visits.",
            )
        visit_data["doctor_id"] = doctor_profile.id

    visit = Visit(**visit_data)
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return VisitResponse.model_validate(visit, from_attributes=True)


@router.get("/patient/{patient_id}", response_model=list[VisitResponse])
def list_patient_visits(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[VisitResponse]:
    ensure_patient_profile_access(db, current_user, patient_id)
    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient_id)
        .order_by(Visit.created_at.desc())
        .all()
    )
    return [VisitResponse.model_validate(item, from_attributes=True) for item in visits]
