from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import DoctorProfile, PatientProfile, User


def get_patient_profile_for_user(db: Session, user: User) -> PatientProfile | None:
    return db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()


def get_doctor_profile_for_user(db: Session, user: User) -> DoctorProfile | None:
    return db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()


def ensure_patient_access(db: Session, user: User, patient_id: int) -> PatientProfile:
    patient = db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile not found.")

    if user.role == "admin":
        return patient

    if user.role == "patient":
        own_profile = get_patient_profile_for_user(db, user)
        if own_profile is None or own_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this patient.",
            )
        return patient

    if user.role == "doctor":
        return patient

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions.",
    )


def ensure_doctor_access(db: Session, user: User, doctor_id: int) -> DoctorProfile:
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    if user.role == "admin":
        return doctor

    if user.role == "doctor":
        own_profile = get_doctor_profile_for_user(db, user)
        if own_profile is None or own_profile.id != doctor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this doctor profile.",
            )
        return doctor

    if user.role == "patient":
        return doctor

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions.",
    )
