from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import DoctorProfile, User
from app.db.session import get_db
from app.schemas.doctor import DoctorProfileResponse, DoctorProfileUpsert
from app.services.clinical_records import assign_department_to_doctor

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _serialize_doctor(profile: DoctorProfile) -> DoctorProfileResponse:
    payload = DoctorProfileResponse.model_validate(profile, from_attributes=True)
    payload.department_name = profile.department.name if profile.department else None
    return payload


@router.get("/", response_model=list[DoctorProfileResponse])
def list_doctors(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[DoctorProfileResponse]:
    profiles = db.query(DoctorProfile).order_by(DoctorProfile.full_name.asc()).all()
    return [_serialize_doctor(profile) for profile in profiles]


@router.get("/specialty/{specialty}", response_model=list[DoctorProfileResponse])
def list_doctors_by_specialty(
    specialty: str,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[DoctorProfileResponse]:
    """Get doctors by specialty."""
    profiles = (
        db.query(DoctorProfile)
        .filter(DoctorProfile.specialty.ilike(f"%{specialty}%"))
        .order_by(DoctorProfile.full_name.asc())
        .all()
    )
    return [_serialize_doctor(profile) for profile in profiles]


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

    assign_department_to_doctor(db, profile)
    db.commit()
    db.refresh(profile)
    return _serialize_doctor(profile)


@router.get("/me", response_model=DoctorProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> DoctorProfileResponse:
    profile = (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return _serialize_doctor(profile)


@router.get("/{doctor_id}", response_model=DoctorProfileResponse)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> DoctorProfileResponse:
    profile = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return _serialize_doctor(profile)
