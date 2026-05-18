from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Appointment,
    AppointmentSlot,
    Clinic,
    DoctorClinic,
    DoctorProfile,
    DoctorSchedule,
)

DEFAULT_SLOT_WINDOW_DAYS = 14
DEFAULT_SLOT_MINUTES = 30
DEFAULT_DEMO_WEEKDAYS = {"sunday", "monday", "tuesday", "wednesday", "thursday"}
DEFAULT_DEMO_START_TIME = time(9, 0)
DEFAULT_DEMO_END_TIME = time(17, 0)
OPEN_SLOT_STATUSES = {"open"}
RESERVED_SLOT_STATUS = "reserved"
BOOKED_SLOT_STATUS = "booked"


class SlotBookingError(Exception):
    """Base slot booking exception."""


class SlotBookingConflict(SlotBookingError):
    """Raised when a slot is no longer available."""


class SlotBookingValidationError(SlotBookingError):
    """Raised when a slot request is invalid."""


@dataclass(frozen=True)
class SlotWindow:
    start_date: date
    end_date: date


def resolve_slot_window(
    start_date: date | None,
    end_date: date | None,
    *,
    default_days: int = DEFAULT_SLOT_WINDOW_DAYS,
) -> SlotWindow:
    resolved_start = start_date or date.today()
    resolved_end = end_date or (resolved_start + timedelta(days=default_days - 1))
    if resolved_end < resolved_start:
        raise SlotBookingValidationError("End date must be on or after start date.")
    return SlotWindow(start_date=resolved_start, end_date=resolved_end)


def _iter_dates(start_date: date, end_date: date) -> Iterable[date]:
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _combine_day_and_time(value_date: date, value_time: time) -> datetime:
    return datetime.combine(value_date, value_time)


def _serialize_weekday(value_date: date) -> str:
    return value_date.strftime("%A").lower()


def _slot_minutes(schedule: DoctorSchedule) -> int:
    return max(schedule.slot_minutes or DEFAULT_SLOT_MINUTES, 5)


def _load_doctor_schedules(
    db: Session,
    doctor_id: int,
) -> list[DoctorSchedule]:
    return (
        db.query(DoctorSchedule)
        .options(
            joinedload(DoctorSchedule.doctor_clinic).joinedload(DoctorClinic.clinic)
        )
        .filter(
            DoctorSchedule.doctor_id == doctor_id, DoctorSchedule.is_active.is_(True)
        )
        .order_by(DoctorSchedule.day_of_week.asc(), DoctorSchedule.start_time.asc())
        .all()
    )


def _ensure_demo_doctor_clinic(db: Session, doctor_id: int) -> DoctorClinic | None:
    primary = get_primary_doctor_clinic(db, doctor_id)
    if primary is not None:
        return primary

    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if doctor is None:
        return None

    clinic_name = doctor.clinic or "Demo Clinic"
    stored_clinic = Clinic(
        name=clinic_name,
        area=doctor.area,
        city=doctor.city,
        is_active=True,
    )
    db.add(stored_clinic)
    db.flush()
    clinic = DoctorClinic(
        doctor_id=doctor.id,
        clinic_id=stored_clinic.id,
        is_primary=True,
        is_active=True,
    )
    db.add(clinic)
    db.flush()
    return clinic


def _build_demo_schedules(
    db: Session,
    doctor_id: int,
    window: SlotWindow,
) -> list[DoctorSchedule]:
    doctor_clinic = _ensure_demo_doctor_clinic(db, doctor_id)
    if doctor_clinic is None:
        return []

    schedules: list[DoctorSchedule] = []
    for weekday in sorted(DEFAULT_DEMO_WEEKDAYS):
        schedules.append(
            DoctorSchedule(
                doctor_id=doctor_id,
                doctor_clinic_id=doctor_clinic.id,
                day_of_week=weekday,
                start_time=DEFAULT_DEMO_START_TIME,
                end_time=DEFAULT_DEMO_END_TIME,
                slot_minutes=DEFAULT_SLOT_MINUTES,
                valid_from=window.start_date,
                valid_to=window.end_date,
                location_label=doctor_clinic.clinic.name,
                is_active=True,
            )
        )
    return schedules


def _get_applicable_schedules(
    db: Session,
    doctor_id: int,
    window: SlotWindow,
) -> list[DoctorSchedule]:
    schedules = _load_doctor_schedules(db, doctor_id)
    if schedules:
        return schedules
    return _build_demo_schedules(db, doctor_id, window)


def _load_existing_slots(
    db: Session,
    doctor_id: int,
    window: SlotWindow,
) -> dict[tuple[int, datetime, datetime], AppointmentSlot]:
    start_at = datetime.combine(window.start_date, time.min)
    end_at = datetime.combine(window.end_date + timedelta(days=1), time.min)
    slots = (
        db.query(AppointmentSlot)
        .join(AppointmentSlot.doctor_clinic)
        .options(
            joinedload(AppointmentSlot.doctor_clinic).joinedload(DoctorClinic.clinic)
        )
        .filter(
            DoctorClinic.doctor_id == doctor_id,
            AppointmentSlot.start_at >= start_at,
            AppointmentSlot.start_at < end_at,
        )
        .all()
    )
    return {(slot.doctor_clinic_id, slot.start_at, slot.end_at): slot for slot in slots}


def generate_slots_for_doctor(
    db: Session,
    doctor_id: int,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[AppointmentSlot]:
    window = resolve_slot_window(start_date, end_date)
    schedules = _get_applicable_schedules(db, doctor_id, window)
    if not schedules:
        return []

    existing_slots = _load_existing_slots(db, doctor_id, window)
    created_any = False

    for current_date in _iter_dates(window.start_date, window.end_date):
        weekday_name = _serialize_weekday(current_date)
        for schedule in schedules:
            if schedule.doctor_clinic_id is None:
                continue
            if schedule.day_of_week.strip().lower() != weekday_name:
                continue
            if schedule.valid_from and current_date < schedule.valid_from:
                continue
            if schedule.valid_to and current_date > schedule.valid_to:
                continue

            slot_delta = timedelta(minutes=_slot_minutes(schedule))
            slot_start = _combine_day_and_time(current_date, schedule.start_time)
            schedule_end = _combine_day_and_time(current_date, schedule.end_time)

            while slot_start + slot_delta <= schedule_end:
                slot_end = slot_start + slot_delta
                key = (schedule.doctor_clinic_id, slot_start, slot_end)
                if key not in existing_slots:
                    slot = AppointmentSlot(
                        doctor_clinic_id=schedule.doctor_clinic_id,
                        schedule_id=schedule.id,
                        start_at=slot_start,
                        end_at=slot_end,
                        status="open",
                    )
                    db.add(slot)
                    existing_slots[key] = slot
                    created_any = True
                slot_start = slot_end

    if created_any:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        existing_slots = _load_existing_slots(db, doctor_id, window)

    return sorted(
        [slot for slot in existing_slots.values() if slot.status in OPEN_SLOT_STATUSES],
        key=lambda slot: slot.start_at,
    )


def reserve_slot_for_appointment(
    db: Session,
    *,
    patient_id: int,
    doctor_id: int,
    reason: str,
    notes: str | None,
    slot_id: int,
    clinic_id: int | None = None,
) -> Appointment:
    slot = (
        db.query(AppointmentSlot)
        .options(
            joinedload(AppointmentSlot.doctor_clinic).joinedload(DoctorClinic.clinic)
        )
        .filter(AppointmentSlot.id == slot_id)
        .first()
    )
    if slot is None:
        raise SlotBookingValidationError("Appointment slot not found.")
    if slot.status not in OPEN_SLOT_STATUSES:
        raise SlotBookingConflict(
            "The selected appointment slot is no longer available."
        )
    if slot.doctor_clinic.doctor_id != doctor_id:
        raise SlotBookingValidationError(
            "Selected slot does not belong to the requested doctor."
        )
    if clinic_id is not None and slot.doctor_clinic.clinic_id != clinic_id:
        raise SlotBookingValidationError(
            "Selected slot does not belong to the requested clinic."
        )

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        clinic_id=slot.doctor_clinic.clinic_id,
        slot_id=slot.id,
        status="requested",
        scheduled_for=slot.start_at,
        reason=reason,
        notes=notes,
    )
    slot.status = RESERVED_SLOT_STATUS
    db.add(appointment)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise SlotBookingConflict(
            "The selected appointment slot is no longer available."
        ) from exc

    db.refresh(appointment)
    return appointment


def sync_slot_status_for_appointment(db: Session, appointment: Appointment) -> None:
    if appointment.slot is None:
        return

    if appointment.status == "approved":
        appointment.slot.status = BOOKED_SLOT_STATUS
        appointment.clinic_id = appointment.slot.doctor_clinic.clinic_id
        appointment.scheduled_for = appointment.slot.start_at
    elif appointment.status == "rejected":
        appointment.slot.status = "open"
        appointment.clinic_id = (
            appointment.clinic_id or appointment.slot.doctor_clinic.clinic_id
        )
        appointment.scheduled_for = (
            appointment.scheduled_for or appointment.slot.start_at
        )
        appointment.slot_id = None

    db.flush()


def scheduled_time_is_available(
    db: Session,
    *,
    doctor_id: int,
    scheduled_for: datetime,
    clinic_id: int | None = None,
) -> bool:
    slots = generate_slots_for_doctor(
        db,
        doctor_id,
        start_date=scheduled_for.date(),
        end_date=scheduled_for.date(),
    )
    return any(
        slot.start_at == scheduled_for
        and (clinic_id is None or slot.doctor_clinic.clinic_id == clinic_id)
        for slot in slots
    )


def load_appointments_with_relations(query):
    return query.options(
        joinedload(Appointment.clinic),
        joinedload(Appointment.slot)
        .joinedload(AppointmentSlot.doctor_clinic)
        .joinedload(DoctorClinic.clinic),
    )


def get_primary_doctor_clinic(db: Session, doctor_id: int) -> DoctorClinic | None:
    return (
        db.query(DoctorClinic)
        .options(joinedload(DoctorClinic.clinic))
        .filter(
            DoctorClinic.doctor_id == doctor_id,
            DoctorClinic.is_active.is_(True),
        )
        .order_by(DoctorClinic.is_primary.desc(), DoctorClinic.id.asc())
        .first()
    )


def load_doctor_with_clinics(db: Session, doctor_id: int) -> DoctorProfile | None:
    return (
        db.query(DoctorProfile)
        .options(
            joinedload(DoctorProfile.doctor_clinics).joinedload(DoctorClinic.clinic)
        )
        .filter(DoctorProfile.id == doctor_id)
        .first()
    )
