from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user, require_roles
from app.db.models import TriageAssessment, User
from app.db.session import get_db
from app.schemas.triage import (
    TriageAssessmentResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.access_control import ensure_patient_profile_access
from app.services.clinical_records import (
    extract_symptom_names,
    persist_triage_assessment,
    sync_patient_symptoms,
)
from app.services.triage_service import triage as run_triage

router = APIRouter(tags=["triage"])


@router.post("/triage", response_model=TriageResponse)
def triage_route(
    payload: TriageRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> TriageResponse:
    response = run_triage(
        payload.query,
        patient_id=payload.patient_id,
        db=db,
        current_user=current_user,
    )
    if payload.patient_id is not None and current_user is not None:
        patient = ensure_patient_profile_access(db, current_user, payload.patient_id)
        persist_triage_assessment(
            db,
            patient=patient,
            query_text=payload.query,
            response=response,
        )
        sync_patient_symptoms(
            db,
            patient=patient,
            symptom_names=extract_symptom_names(payload.query),
            source="triage",
            notes=response.suspected_condition,
        )
        db.commit()
    return response


def _serialize_assessment(item: TriageAssessment) -> TriageAssessmentResponse:
    return TriageAssessmentResponse(
        id=item.id,
        patient_id=item.patient_id,
        appointment_id=item.appointment_id,
        query_text=item.query_text,
        created_at=item.created_at,
        triage_level=item.triage_level,
        urgency_level=item.urgency_level,
        urgency_label=item.urgency_label,
        urgency_reason=item.urgency_reason,
        summary=item.summary,
        clinical_summary=item.clinical_summary,
        simple_reasoning=item.simple_reasoning,
        plain_language_explanation=item.plain_language_explanation,
        patient_friendly_explanation=item.patient_friendly_explanation,
        actions=item.actions,
        recommended_actions=item.recommended_actions,
        red_flags=item.red_flags,
        recommended_specialty=item.recommended_specialty,
        specialty_reason=item.specialty_reason,
        suspected_condition=item.suspected_condition,
        suspected_conditions=item.suspected_conditions,
        suggested_doctors=item.suggested_doctors,
        supporting_references=item.supporting_references,
        disclaimer=item.disclaimer,
        history_used=item.history_used,
    )


@router.get(
    "/triage/history/{patient_id}",
    response_model=list[TriageAssessmentResponse],
)
def list_triage_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[TriageAssessmentResponse]:
    ensure_patient_profile_access(db, current_user, patient_id)
    items = (
        db.query(TriageAssessment)
        .filter(TriageAssessment.patient_id == patient_id)
        .order_by(TriageAssessment.created_at.desc())
        .all()
    )
    return [_serialize_assessment(item) for item in items]
