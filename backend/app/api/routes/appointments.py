from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
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
    ensure_doctor_access,
    ensure_patient_access,
    get_doctor_profile_for_user,
    get_patient_profile_for_user,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "admin")),
) -> AppointmentResponse:
    patient = ensure_patient_access(db, current_user, payload.patient_id)
    ensure_doctor_access(db, current_user, payload.doctor_id)

    if current_user.role == "patient":
        own_profile = get_patient_profile_for_user(db, current_user)
        if own_profile is None or own_profile.id != patient.id:
            raise HTTPException(
                status_code=403, detail="You can only book for yourself."
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

    if current_user.role == "doctor":
        own_profile = get_doctor_profile_for_user(db, current_user)
        if own_profile is None or own_profile.id != appointment.doctor_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have access to this appointment.",
            )

    appointment.status = payload.status
    appointment.notes = payload.notes or appointment.notes
    db.commit()
    db.refresh(appointment)
    return AppointmentResponse.model_validate(appointment, from_attributes=True)


@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[AppointmentResponse]:
    query = db.query(Appointment)

    if current_user.role == "patient":
        own_profile = get_patient_profile_for_user(db, current_user)
        if own_profile is None:
            return []
        query = query.filter(Appointment.patient_id == own_profile.id)
    elif current_user.role == "doctor":
        own_profile = get_doctor_profile_for_user(db, current_user)
        if own_profile is None:
            return []
        query = query.filter(Appointment.doctor_id == own_profile.id)

    appointments = (
        query.order_by(Appointment.requested_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AppointmentResponse.model_validate(item, from_attributes=True)
        for item in appointments
    ]
