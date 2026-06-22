from __future__ import annotations

from datetime import date, timedelta

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
from app.services.clinical_records import (
    extract_symptom_names,
    sync_medical_history_from_visit,
    sync_patient_symptoms,
)

router = APIRouter(prefix="/visits", tags=["visits"])


def _suggest_follow_up_items(payload: VisitCreate) -> list[str]:
    text = " ".join(
        item or ""
        for item in (
            payload.symptoms,
            payload.diagnosis,
            payload.notes,
            payload.prescriptions,
        )
    ).lower()
    suggestions: list[str] = []
    if payload.prescriptions:
        suggestions.append("Review medication response and side effects.")
    if any(term in text for term in ("asthma", "wheez", "bronch", "cough")):
        suggestions.append("Check breathing symptoms and inhaler response.")
    if any(term in text for term in ("pain", "injury", "strain", "back")):
        suggestions.append("Reassess pain, mobility, and functional limitation.")
    if any(term in text for term in ("diabetes", "pressure", "hypertension")):
        suggestions.append("Review home measurements and control trend.")
    if not suggestions:
        suggestions.append("Check whether symptoms improved, persisted, or worsened.")
    return suggestions[:4]


@router.post("/", response_model=VisitResponse)
def create_visit(
    payload: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> VisitResponse:
    patient = get_patient_profile_or_404(db, payload.patient_id)
    visit_data = payload.model_dump()
    if not visit_data.get("follow_up_recommendations"):
        visit_data["follow_up_recommendations"] = _suggest_follow_up_items(payload)
    if not visit_data.get("follow_up_due_on"):
        visit_data["follow_up_due_on"] = date.today() + timedelta(days=14)
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
    db.flush()
    sync_medical_history_from_visit(db, visit=visit, source_type="visit")
    sync_patient_symptoms(
        db,
        patient=patient,
        symptom_names=extract_symptom_names(visit.symptoms),
        source="visit",
        notes=visit.diagnosis or visit.notes,
        observed_at=visit.created_at,
    )
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


@router.get("/", response_model=list[VisitResponse])
def list_visits(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> list[VisitResponse]:
    query = db.query(Visit)
    if current_user.role == "doctor":
        doctor_profile = get_linked_doctor_profile(db, current_user)
        if doctor_profile is None:
            return []
        query = query.filter(Visit.doctor_id == doctor_profile.id)

    visits = query.order_by(Visit.created_at.desc()).all()
    return [VisitResponse.model_validate(item, from_attributes=True) for item in visits]
