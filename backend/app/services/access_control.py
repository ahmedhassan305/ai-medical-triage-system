from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import Appointment, DoctorProfile, PatientProfile, User


def get_linked_patient_profile(
    db: Session,
    current_user: User,
) -> PatientProfile | None:
    return (
        db.query(PatientProfile)
        .filter(PatientProfile.user_id == current_user.id)
        .first()
    )


def get_linked_doctor_profile(
    db: Session,
    current_user: User,
) -> DoctorProfile | None:
    return (
        db.query(DoctorProfile).filter(DoctorProfile.user_id == current_user.id).first()
    )


def require_linked_patient_profile(
    db: Session,
    current_user: User,
) -> PatientProfile:
    profile = get_linked_patient_profile(db, current_user)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient profile is required for this action.",
        )
    return profile


def require_linked_doctor_profile(
    db: Session,
    current_user: User,
) -> DoctorProfile:
    profile = get_linked_doctor_profile(db, current_user)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor profile is required for this action.",
        )
    return profile


def get_patient_profile_or_404(db: Session, patient_id: int) -> PatientProfile:
    profile = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")
    return profile


def get_doctor_profile_or_404(db: Session, doctor_id: int) -> DoctorProfile:
    profile = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    return profile


def ensure_patient_profile_access(
    db: Session,
    current_user: User,
    patient_id: int,
) -> PatientProfile:
    patient_profile = get_patient_profile_or_404(db, patient_id)
    if current_user.role == "admin":
        return patient_profile

    if current_user.role == "doctor":
        require_linked_doctor_profile(db, current_user)
        return patient_profile

    if current_user.role == "patient":
        own_profile = require_linked_patient_profile(db, current_user)
        if own_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own patient data.",
            )
        return patient_profile

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions.",
    )


def ensure_appointment_status_access(
    db: Session,
    current_user: User,
    appointment: Appointment,
) -> None:
    if current_user.role == "admin":
        return

    doctor_profile = require_linked_doctor_profile(db, current_user)
    if appointment.doctor_id != doctor_profile.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage appointments assigned to you.",
        )
