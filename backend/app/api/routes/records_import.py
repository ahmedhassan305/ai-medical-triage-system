from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import PatientProfile, User, Visit
from app.db.session import get_db
from app.schemas.records import RecordsImportResult
from app.services.clinical_records import (
    extract_symptom_names,
    sync_medical_history_from_visit,
    sync_patient_symptoms,
)

router = APIRouter(prefix="/records", tags=["records"])


def _parse_records(filename: str, content: str) -> list[dict[str, object]]:
    lower = filename.lower()
    if lower.endswith(".json"):
        payload = json.loads(content)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            records = payload.get("records")
            if isinstance(records, list):
                return [item for item in records if isinstance(item, dict)]
        raise ValueError("Invalid JSON records payload.")

    if lower.endswith(".csv"):
        reader = csv.DictReader(io.StringIO(content))
        return [dict(row) for row in reader]

    raise ValueError("Unsupported file type. Use JSON or CSV.")


@router.post("/import", response_model=RecordsImportResult)
def import_records(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> RecordsImportResult:
    patient = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    try:
        content = file.file.read().decode("utf-8")
        records = _parse_records(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    imported = 0
    for record in records:
        symptoms = str(record.get("symptoms", "")).strip()
        if not symptoms:
            continue
        visit = Visit(
            patient_id=patient_id,
            doctor_id=(int(record["doctor_id"]) if record.get("doctor_id") else None),
            symptoms=symptoms,
            diagnosis=(
                str(record["diagnosis"]).strip() if record.get("diagnosis") else None
            ),
            notes=(str(record["notes"]).strip() if record.get("notes") else None),
            prescriptions=(
                str(record["prescriptions"]).strip()
                if record.get("prescriptions")
                else None
            ),
            attachments=None,
            vitals=None,
        )
        db.add(visit)
        db.flush()
        sync_medical_history_from_visit(db, visit=visit, source_type="imported_record")
        sync_patient_symptoms(
            db,
            patient=patient,
            symptom_names=extract_symptom_names(symptoms),
            source="imported_record",
            notes=(str(record["diagnosis"]).strip() if record.get("diagnosis") else None),
            observed_at=visit.created_at,
        )
        imported += 1

    db.commit()
    return RecordsImportResult(imported=imported, patient_id=patient_id)
