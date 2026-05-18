from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.db.models import PatientLabResult, TriageAssessment, User
from app.db.session import get_db
from app.schemas.triage import (
    LabPdfExtractionResponse,
    LabValue,
    TriageAssessmentResponse,
    TriageRequest,
    TriageResponse,
)
from app.services.access_control import ensure_patient_profile_access
from app.services.clinical_records import persist_triage_assessment
from app.services.lab_pdf_extraction import extract_lab_values_from_pdf
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
        lab_values=payload.lab_values,
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


@router.post("/triage/lab-pdf/extract", response_model=LabPdfExtractionResponse)
async def extract_lab_pdf_route(
    patient_id: int | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> LabPdfExtractionResponse:
    if file.content_type != "application/pdf" and not file.filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted.")

    patient = None
    if patient_id is not None:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required to attach lab values.",
            )
        patient = ensure_patient_profile_access(db, current_user, patient_id)

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF file is too large.")

    try:
        values = extract_lab_values_from_pdf(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if patient is not None:
        for value in values:
            db.add(
                PatientLabResult(
                    patient_id=patient.id,
                    lab_name=value.lab_name,
                    value=value.value,
                    unit=value.unit,
                    reference_range=value.reference_range,
                    source_filename=file.filename,
                )
            )
        db.commit()

    return LabPdfExtractionResponse(
        filename=file.filename,
        values=[LabValue(**value.__dict__) for value in values],
    )


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
