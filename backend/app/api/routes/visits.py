from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import User, Visit
from app.db.session import get_db
from app.schemas.visit import VisitCreate, VisitResponse
from app.services.access_control import ensure_patient_access

router = APIRouter(prefix="/visits", tags=["visits"])


@router.post("/", response_model=VisitResponse)
def create_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> VisitResponse:
    ensure_patient_access(db, current_user, payload.patient_id)
    visit = Visit(**payload.model_dump())
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return VisitResponse.model_validate(visit, from_attributes=True)


@router.get("/patient/{patient_id}", response_model=list[VisitResponse])
def list_patient_visits(
    patient_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[VisitResponse]:
    ensure_patient_access(db, current_user, patient_id)
    visits = (
        db.query(Visit)
        .filter(Visit.patient_id == patient_id)
        .order_by(Visit.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [VisitResponse.model_validate(item, from_attributes=True) for item in visits]
