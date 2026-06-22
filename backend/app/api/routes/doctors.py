from __future__ import annotations

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.models import (
    Appointment,
    AppointmentSlot,
    Clinic,
    DoctorClinic,
    DoctorProfile,
    DoctorReview,
    DoctorSchedule,
    User,
    Visit,
)
from app.db.session import get_db
from app.schemas.doctor import (
    AppointmentSlotResponse,
    ClinicResponse,
    DoctorProfileResponse,
    DoctorProfileUpsert,
    DoctorReviewCreate,
    DoctorReviewResponse,
    DoctorScheduleCreate,
    DoctorScheduleResponse,
)
from app.services.access_control import (
    get_linked_patient_profile,
    require_linked_doctor_profile,
)
from app.services.clinical_records import assign_department_to_doctor
from app.services.slot_booking import (
    SlotBookingValidationError,
    generate_slots_for_doctor,
    get_primary_doctor_clinic,
)

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _serialize_doctor(profile: DoctorProfile) -> DoctorProfileResponse:
    payload = DoctorProfileResponse.model_validate(profile, from_attributes=True)
    payload.department_name = profile.department.name if profile.department else None
    ratings = [review.rating for review in profile.reviews]
    payload.review_count = len(ratings)
    payload.rating = round(sum(ratings) / len(ratings), 1) if ratings else None
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


def _default_doctor_clinic_id(db: Session, doctor_id: int) -> int | None:
    doctor_clinic = get_primary_doctor_clinic(db, doctor_id)
    return doctor_clinic.id if doctor_clinic else None


def _clear_future_open_slots(db: Session, doctor_id: int) -> None:
    """Remove generated open slots so schedule edits recalculate availability."""
    today_start = datetime.combine(date.today(), time.min)
    doctor_clinic_ids = select(DoctorClinic.id).filter(
        DoctorClinic.doctor_id == doctor_id
    )
    (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.status == "open",
            AppointmentSlot.start_at >= today_start,
            AppointmentSlot.doctor_clinic_id.in_(doctor_clinic_ids),
        )
        .delete(synchronize_session=False)
    )


def _ensure_doctor_schedule_access(
    db: Session,
    current_user: User,
    doctor_id: int,
) -> None:
    if current_user.role == "admin":
        return
    linked_doctor = require_linked_doctor_profile(db, current_user)
    if linked_doctor.id != doctor_id:
        raise HTTPException(
            status_code=403,
            detail="Doctors can only manage their own schedule.",
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


@router.post(
    "/reviews",
    response_model=DoctorReviewResponse,
    status_code=201,
)
def create_doctor_review(
    payload: DoctorReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("patient")),
) -> DoctorReviewResponse:
    patient = get_linked_patient_profile(db, current_user)
    if patient is None:
        raise HTTPException(
            status_code=403,
            detail="Patient profile is required before reviewing doctors.",
        )
    if (
        db.query(DoctorProfile).filter(DoctorProfile.id == payload.doctor_id).first()
        is None
    ):
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    if payload.appointment_id is not None:
        appointment = (
            db.query(Appointment)
            .filter(Appointment.id == payload.appointment_id)
            .first()
        )
        if (
            appointment is None
            or appointment.patient_id != patient.id
            or appointment.doctor_id != payload.doctor_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Patients can only review doctors from their own bookings.",
            )
    if payload.visit_id is not None:
        visit = db.query(Visit).filter(Visit.id == payload.visit_id).first()
        if (
            visit is None
            or visit.patient_id != patient.id
            or visit.doctor_id != payload.doctor_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Patients can only review doctors from their own visits.",
            )

    review = DoctorReview(
        patient_id=patient.id,
        doctor_id=payload.doctor_id,
        appointment_id=payload.appointment_id,
        visit_id=payload.visit_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return DoctorReviewResponse.model_validate(review, from_attributes=True)


@router.get("/{doctor_id}/rating")
def get_doctor_rating(
    doctor_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_roles("patient", "doctor", "admin")),
) -> dict[str, float | int | None]:
    if db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    average, count = (
        db.query(func.avg(DoctorReview.rating), func.count(DoctorReview.id))
        .filter(DoctorReview.doctor_id == doctor_id)
        .one()
    )
    return {
        "doctor_id": doctor_id,
        "rating": round(float(average), 1) if average is not None else None,
        "review_count": int(count or 0),
    }


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
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> list[DoctorScheduleResponse]:
    if db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    _ensure_doctor_schedule_access(db, current_user, doctor_id)
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
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> DoctorScheduleResponse:
    if db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first() is None:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
    _ensure_doctor_schedule_access(db, current_user, doctor_id)
    schedule_data = payload.model_dump()
    if schedule_data.get("doctor_clinic_id") is None:
        schedule_data["doctor_clinic_id"] = _default_doctor_clinic_id(db, doctor_id)
    schedule = DoctorSchedule(doctor_id=doctor_id, **schedule_data)
    db.add(schedule)
    _clear_future_open_slots(db, doctor_id)
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
    current_user: User = Depends(require_roles("doctor", "admin")),
) -> DoctorScheduleResponse:
    _ensure_doctor_schedule_access(db, current_user, doctor_id)
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
    schedule_data = payload.model_dump()
    if schedule_data.get("doctor_clinic_id") is None:
        schedule_data["doctor_clinic_id"] = (
            schedule.doctor_clinic_id or _default_doctor_clinic_id(db, doctor_id)
        )
    for key, value in schedule_data.items():
        setattr(schedule, key, value)
    _clear_future_open_slots(db, doctor_id)
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
