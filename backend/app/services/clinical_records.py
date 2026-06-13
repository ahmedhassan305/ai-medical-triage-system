from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.models import (
    Department,
    DoctorProfile,
    MedicalHistory,
    PatientProfile,
    PatientSymptom,
    Symptom,
    TriageAssessment,
    Visit,
)
from app.patient_symptoms import PATIENT_SYMPTOM_KEYWORDS
from app.schemas.triage import TriageResponse


def normalize_department_name(value: str) -> str:
    return value.strip() or "General Medicine"


def get_or_create_department(db: Session, name: str) -> Department:
    normalized_name = normalize_department_name(name)
    department = db.query(Department).filter(Department.name == normalized_name).first()
    if department is not None:
        return department

    department = Department(
        name=normalized_name,
        description=f"{normalized_name} department",
    )
    db.add(department)
    db.flush()
    return department


def assign_department_to_doctor(
    db: Session,
    doctor: DoctorProfile,
    *,
    department_name: str | None = None,
) -> None:
    resolved_name = department_name or doctor.specialty or "General Medicine"
    department = get_or_create_department(db, resolved_name)
    doctor.department_id = department.id


def extract_symptom_names(text: str) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []
    for keyword, _condition in PATIENT_SYMPTOM_KEYWORDS:
        if keyword in lowered and keyword not in matches:
            matches.append(keyword)
    return matches[:12]


def get_or_create_symptom(
    db: Session,
    *,
    name: str,
    category: str | None = None,
) -> Symptom:
    normalized_name = name.strip().lower()
    symptom = db.query(Symptom).filter(Symptom.name == normalized_name).first()
    if symptom is not None:
        return symptom

    symptom = Symptom(name=normalized_name, category=category)
    db.add(symptom)
    db.flush()
    return symptom


def sync_patient_symptoms(
    db: Session,
    *,
    patient: PatientProfile,
    symptom_names: list[str],
    source: str,
    notes: str | None = None,
    observed_at: datetime | None = None,
) -> None:
    timestamp = observed_at or datetime.now(UTC).replace(tzinfo=None)
    for symptom_name in symptom_names:
        symptom = get_or_create_symptom(db, name=symptom_name)
        link = (
            db.query(PatientSymptom)
            .filter(
                PatientSymptom.patient_id == patient.id,
                PatientSymptom.symptom_id == symptom.id,
            )
            .first()
        )
        if link is None:
            link = PatientSymptom(
                patient_id=patient.id,
                symptom_id=symptom.id,
                source=source,
                notes=notes,
                first_recorded_at=timestamp,
                last_recorded_at=timestamp,
            )
            db.add(link)
            continue

        link.source = source
        if notes:
            link.notes = notes
        link.last_recorded_at = timestamp


def sync_medical_history_from_visit(
    db: Session,
    *,
    visit: Visit,
    source_type: str,
) -> MedicalHistory:
    entry = db.query(MedicalHistory).filter(MedicalHistory.visit_id == visit.id).first()
    if entry is None:
        entry = MedicalHistory(
            patient_id=visit.patient_id,
            doctor_id=visit.doctor_id,
            visit_id=visit.id,
            appointment_id=visit.appointment_id,
            source_type=source_type,
            condition_name=visit.diagnosis,
            symptoms_summary=visit.symptoms,
            diagnosis=visit.diagnosis,
            notes=visit.notes,
            prescriptions=visit.prescriptions,
            vitals=visit.vitals,
            attachments=visit.attachments,
            recorded_at=visit.created_at,
        )
        db.add(entry)
        return entry

    entry.patient_id = visit.patient_id
    entry.doctor_id = visit.doctor_id
    entry.appointment_id = visit.appointment_id
    entry.source_type = source_type
    entry.condition_name = visit.diagnosis
    entry.symptoms_summary = visit.symptoms
    entry.diagnosis = visit.diagnosis
    entry.notes = visit.notes
    entry.prescriptions = visit.prescriptions
    entry.vitals = visit.vitals
    entry.attachments = visit.attachments
    entry.recorded_at = visit.created_at
    return entry


def persist_triage_assessment(
    db: Session,
    *,
    patient: PatientProfile,
    query_text: str,
    response: TriageResponse,
    appointment_id: int | None = None,
) -> TriageAssessment:
    assessment = TriageAssessment(
        patient_id=patient.id,
        appointment_id=appointment_id,
        query_text=query_text,
        triage_level=response.triage_level,
        urgency_level=response.urgency_level,
        urgency_label=response.urgency_label,
        urgency_reason=response.urgency_reason,
        summary=response.summary,
        clinical_summary=response.clinical_summary,
        simple_reasoning=response.simple_reasoning,
        plain_language_explanation=response.plain_language_explanation,
        patient_friendly_explanation=response.patient_friendly_explanation,
        actions=response.actions,
        recommended_actions=response.recommended_actions,
        red_flags=response.red_flags,
        recommended_specialty=response.recommended_specialty,
        specialty_reason=response.specialty_reason,
        suspected_condition=response.suspected_condition,
        suspected_conditions=[
            item.model_dump() for item in response.suspected_conditions
        ],
        suggested_doctors=[item.model_dump() for item in response.suggested_doctors],
        supporting_references=[
            item.model_dump() for item in response.supporting_references
        ],
        disclaimer=response.disclaimer,
        history_used=response.history_used,
    )
    db.add(assessment)
    return assessment
