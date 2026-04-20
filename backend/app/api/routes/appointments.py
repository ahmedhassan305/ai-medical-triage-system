from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import Appointment, User
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
)
from app.services.access_control import (
    ensure_appointment_status_access,
    get_doctor_profile_or_404,
    get_linked_doctor_profile,
    get_linked_patient_profile,
    get_patient_profile_or_404,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> AppointmentResponse:
    patient = get_patient_profile_or_404(db, payload.patient_id)
    get_doctor_profile_or_404(db, payload.doctor_id)

    if current_user.role == "patient":
        own_patient_profile = get_linked_patient_profile(db, current_user)
        if own_patient_profile is None:
            raise HTTPException(
                status_code=403,
                detail="Patient profile is required before booking appointments.",
            )
        if own_patient_profile.id != patient.id:
            raise HTTPException(
                status_code=403,
                detail="Patients can only book appointments for themselves.",
            )

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
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> AppointmentResponse:
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    ensure_appointment_status_access(db, current_user, appointment)
    appointment.status = payload.status
    appointment.notes = payload.notes or appointment.notes
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment, from_attributes=True)


@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[AppointmentResponse]:
    query = db.query(Appointment)
    if current_user.role == "patient":
        patient_profile = get_linked_patient_profile(db, current_user)
        if patient_profile is None:
            return []
        query = query.filter(Appointment.patient_id == patient_profile.id)
    elif current_user.role == "doctor":
        doctor_profile = get_linked_doctor_profile(db, current_user)
        if doctor_profile is None:
            return []
        query = query.filter(Appointment.doctor_id == doctor_profile.id)

    appointments = query.order_by(Appointment.requested_at.desc()).all()
    return [
        AppointmentResponse.model_validate(item, from_attributes=True)
        for item in appointments
    ]
