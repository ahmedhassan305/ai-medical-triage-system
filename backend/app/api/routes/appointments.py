from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import Appointment, DoctorProfile, PatientProfile, User
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "admin")),
) -> AppointmentResponse:
    patient = (
        db.query(PatientProfile).filter(PatientProfile.id == payload.patient_id).first()
    )
    doctor = (
        db.query(DoctorProfile).filter(DoctorProfile.id == payload.doctor_id).first()
    )
    if patient is None or doctor is None:
        raise HTTPException(status_code=404, detail="Patient or doctor not found.")

    appointment = Appointment(**payload.model_dump(), status="requested")
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment, from_attributes=True)


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> AppointmentResponse:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    appointment.status = payload.status
    appointment.notes = payload.notes or appointment.notes
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment, from_attributes=True)


@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[AppointmentResponse]:
    appointments = db.query(Appointment).order_by(Appointment.requested_at.desc()).all()
    return [
        AppointmentResponse.model_validate(item, from_attributes=True)
        for item in appointments
    ]
