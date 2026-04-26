from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import PatientProfile, User
from app.db.session import get_db
from app.schemas.patient import PatientProfileResponse, PatientProfileUpsert

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=list[PatientProfileResponse])
def list_patients(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> list[PatientProfileResponse]:
    profiles = db.query(PatientProfile).order_by(PatientProfile.full_name.asc()).all()
    return [
        PatientProfileResponse.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


@router.post("/me", response_model=PatientProfileResponse)
def upsert_my_profile(
    payload: PatientProfileUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> PatientProfileResponse:
    profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        profile = PatientProfile(user_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/me", response_model=PatientProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> PatientProfileResponse:
    profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return PatientProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/{patient_id}", response_model=PatientProfileResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> PatientProfileResponse:
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return PatientProfileResponse.model_validate(profile, from_attributes=True)
