from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models import DoctorProfile, User
from app.db.session import get_db
from app.schemas.doctor import DoctorProfileResponse, DoctorProfileUpsert

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/", response_model=list[DoctorProfileResponse])
def list_doctors(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[DoctorProfileResponse]:
    profiles = db.query(DoctorProfile).order_by(DoctorProfile.full_name.asc()).all()
    return [
        DoctorProfileResponse.model_validate(profile, from_attributes=True)
        for profile in profiles
    ]


@router.post("/me", response_model=DoctorProfileResponse)
def upsert_my_profile(
    payload: DoctorProfileUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> DoctorProfileResponse:
    profile = (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    )
    if profile is None:
        profile = DoctorProfile(user_id=current_user.id, **payload.model_dump())
        db.add(profile)
    else:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return DoctorProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/me", response_model=DoctorProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DoctorProfileResponse:
    profile = (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return DoctorProfileResponse.model_validate(profile, from_attributes=True)


@router.get("/{doctor_id}", response_model=DoctorProfileResponse)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> DoctorProfileResponse:
    profile = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return DoctorProfileResponse.model_validate(profile, from_attributes=True)
