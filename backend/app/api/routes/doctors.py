from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import AppointmentSlot, Clinic, DoctorProfile, DoctorSchedule, User
from app.db.session import get_db
from app.schemas.doctor import (
    AppointmentSlotResponse,
    ClinicResponse,
    DoctorProfileResponse,
    DoctorProfileUpsert,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
)
from app.services.clinical_records import assign_department_to_doctor
from app.services.slot_booking import (
    SlotBookingValidationError,
    generate_slots_for_doctor,
)

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _serialize_doctor(profile: DoctorProfile) -> DoctorProfileResponse:
    payload = DoctorProfileResponse.model_validate(profile, from_attributes=True)
    payload.department_name = profile.department.name if profile.department else None
    return payload


def _serialize_clinic(clinic: Clinic | None) -> ClinicResponse | None:
    if clinic is None:
        return None
    return ClinicResponse.model_validate(clinic, from_attributes=True)


def _serialize_slot(slot: AppointmentSlot) -> AppointmentSlotResponse:
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


@router.patch("/{doctor_id}", response_model=DoctorProfileResponse)
def update_doctor(
    doctor_id: int,
    payload: DoctorProfileUpsert,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
) -> DoctorProfileResponse:
    profile = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    assign_department_to_doctor(db, profile)
    db.commit()
    db.refresh(profile)
    return _serialize_doctor(profile)


@router.get("/{doctor_id}/schedules", response_model=list[DoctorScheduleResponse])
def list_doctor_schedules(
    doctor_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("doctor", "admin")),
) -> list[DoctorScheduleResponse]:
    if db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    schedules = (
        db.query(DoctorSchedule)
        .filter(DoctorSchedule.doctor_id == doctor_id)
        .order_by(DoctorSchedule.day_of_week.asc(), DoctorSchedule.start_time.asc())
        .all()
    )
    return [
        DoctorScheduleResponse.model_validate(schedule, from_attributes=True)
        for schedule in schedules
    ]


@router.post(
    "/{doctor_id}/schedules",
    response_model=DoctorScheduleResponse,
    status_code=201,
)
def create_doctor_schedule(
    doctor_id: int,
    payload: DoctorScheduleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
) -> DoctorScheduleResponse:
    if db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    schedule = DoctorSchedule(doctor_id=doctor_id, **payload.model_dump())
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return DoctorScheduleResponse.model_validate(schedule, from_attributes=True)


@router.patch(
    "/{doctor_id}/schedules/{schedule_id}",
    response_model=DoctorScheduleResponse,
)
def update_doctor_schedule(
    doctor_id: int,
    schedule_id: int,
    payload: DoctorScheduleCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
) -> DoctorScheduleResponse:
    schedule = (
        db.query(DoctorSchedule)
        .filter(
            DoctorSchedule.id == schedule_id,
            DoctorSchedule.doctor_id == doctor_id,
        )
        .first()
    )
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found.")
    for key, value in payload.model_dump().items():
        setattr(schedule, key, value)
    db.commit()
    db.refresh(schedule)
    return DoctorScheduleResponse.model_validate(schedule, from_attributes=True)


@router.get("/{doctor_id}/slots", response_model=list[AppointmentSlotResponse])
def list_doctor_slots(
    doctor_id: int,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> list[AppointmentSlotResponse]:
    profile = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    try:
        slots = generate_slots_for_doctor(
            db,
            doctor_id,
            start_date=start_date,
            end_date=end_date,
        )
    except SlotBookingValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return [_serialize_slot(slot) for slot in slots]
