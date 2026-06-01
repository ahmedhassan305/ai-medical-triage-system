from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import Appointment, AppointmentSlot, Clinic, User
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
)
from app.schemas.doctor import AppointmentSlotResponse, ClinicResponse
from app.services.access_control import (
    ensure_appointment_status_access,
    get_doctor_profile_or_404,
    get_linked_doctor_profile,
    get_linked_patient_profile,
    get_patient_profile_or_404,
)
from app.services.slot_booking import (
    SlotBookingConflict,
    SlotBookingValidationError,
    get_primary_doctor_clinic,
    load_appointments_with_relations,
    reserve_slot_for_appointment,
    scheduled_time_is_available,
    sync_slot_status_for_appointment,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _serialize_clinic(clinic: Clinic | None) -> ClinicResponse | None:
    if clinic is None:
        return None
    return ClinicResponse.model_validate(clinic, from_attributes=True)


def _serialize_slot(slot: AppointmentSlot | None) -> AppointmentSlotResponse | None:
    if slot is None:
        return None
    clinic = slot.doctor_clinic.clinic if slot.doctor_clinic else None
    return AppointmentSlotResponse(
        id=slot.id,
        doctor_clinic_id=slot.doctor_clinic_id,
        schedule_id=slot.schedule_id,
        start_at=slot.start_at,
        end_at=slot.end_at,
        status=slot.status,
        clinic=_serialize_clinic(clinic),
    )


def _serialize_appointment(appointment: Appointment) -> AppointmentResponse:
    clinic = appointment.clinic
    if clinic is None and appointment.slot and appointment.slot.doctor_clinic:
        clinic = appointment.slot.doctor_clinic.clinic
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        reason=appointment.reason,
        notes=appointment.notes,
        scheduled_for=appointment.scheduled_for,
        clinic_id=appointment.clinic_id,
        slot_id=appointment.slot_id,
        status=appointment.status,
        requested_at=appointment.requested_at,
        clinic=_serialize_clinic(clinic),
        slot=_serialize_slot(appointment.slot),
    )


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

    if payload.slot_id is not None:
        try:
            appointment = reserve_slot_for_appointment(
                db,
                patient_id=payload.patient_id,
                doctor_id=payload.doctor_id,
                reason=payload.reason,
                notes=payload.notes,
                slot_id=payload.slot_id,
                clinic_id=payload.clinic_id,
            )
        except SlotBookingValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except SlotBookingConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        appointment = (
            load_appointments_with_relations(db.query(Appointment))
            .filter(Appointment.id == appointment.id)
            .first()
        )
        assert appointment is not None
        return _serialize_appointment(appointment)

    resolved_clinic_id = payload.clinic_id
    if resolved_clinic_id is None:
        primary_doctor_clinic = get_primary_doctor_clinic(db, payload.doctor_id)
        if primary_doctor_clinic is not None:
            resolved_clinic_id = primary_doctor_clinic.clinic_id
    if payload.scheduled_for is not None and not scheduled_time_is_available(
        db,
        doctor_id=payload.doctor_id,
        scheduled_for=payload.scheduled_for,
        clinic_id=resolved_clinic_id,
    ):
        raise HTTPException(
            status_code=422,
            detail="Requested time is outside the doctor's available schedule.",
        )
    if resolved_clinic_id is None:
        primary_doctor_clinic = get_primary_doctor_clinic(db, payload.doctor_id)
        if primary_doctor_clinic is not None:
            resolved_clinic_id = primary_doctor_clinic.clinic_id
    if payload.scheduled_for is not None:
        existing_appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == payload.doctor_id,
                Appointment.scheduled_for == payload.scheduled_for,
                Appointment.status.in_(["requested", "approved"]),
            )
            .first()
        )
        if existing_appointment is not None:
            raise HTTPException(
                status_code=409,
                detail="This appointment time is no longer available.",
            )

    appointment = Appointment(**payload.model_dump(), status="requested")
    appointment.clinic_id = resolved_clinic_id
    db.add(appointment)
    db.commit()
    appointment = (
        load_appointments_with_relations(db.query(Appointment))
        .filter(Appointment.id == appointment.id)
        .first()
    )
    assert appointment is not None
    return _serialize_appointment(appointment)


@router.patch("/{appointment_id}/status", response_model=AppointmentResponse)
def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> AppointmentResponse:
    appointment = (
        load_appointments_with_relations(db.query(Appointment))
        .filter(Appointment.id == appointment_id)
        .first()
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    ensure_appointment_status_access(db, current_user, appointment)
    appointment.status = payload.status
    appointment.notes = payload.notes or appointment.notes
    sync_slot_status_for_appointment(db, appointment)
    db.commit()
    appointment = (
        load_appointments_with_relations(db.query(Appointment))
        .filter(Appointment.id == appointment_id)
        .first()
    )
    assert appointment is not None
    return _serialize_appointment(appointment)


@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[AppointmentResponse]:
    query = load_appointments_with_relations(db.query(Appointment))
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
    return [_serialize_appointment(item) for item in appointments]
