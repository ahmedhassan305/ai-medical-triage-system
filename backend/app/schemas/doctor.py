from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class DoctorProfileUpsert(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    specialty: str = Field(min_length=1, max_length=120)
    clinic: str = Field(min_length=1, max_length=200)
    area: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)


class DoctorProfileResponse(DoctorProfileUpsert):
    id: int
    user_id: int | None = None
    department_id: int | None = None
    department_name: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    booking_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ClinicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str | None = None
    area: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    is_active: bool


class DoctorClinicResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    clinic_id: int
    scope_at_clinic: str | None = None
    is_primary: bool
    is_active: bool
    clinic: ClinicResponse


class AppointmentSlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_clinic_id: int
    schedule_id: int | None = None
    start_at: datetime
    end_at: datetime
    status: str
    clinic: ClinicResponse


class DoctorScheduleCreate(BaseModel):
    doctor_clinic_id: int | None = None
    day_of_week: str = Field(min_length=1, max_length=20)
    start_time: time
    end_time: time
    slot_minutes: int = Field(default=30, ge=5, le=240)
    valid_from: date | None = None
    valid_to: date | None = None
    location_label: str | None = Field(default=None, max_length=200)
    is_active: bool = True


class DoctorScheduleResponse(DoctorScheduleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: int
    created_at: datetime
    updated_at: datetime
