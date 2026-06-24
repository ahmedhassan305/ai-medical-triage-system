from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.doctor import AppointmentSlotResponse, ClinicResponse


class AppointmentTriageSummary(BaseModel):
    triage_level: str
    urgency_level: str
    chief_complaint: str
    clinical_summary: str
    recommended_specialty: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    suspected_conditions: list[dict[str, str]] = Field(default_factory=list)


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    reason: str = Field(min_length=1)
    notes: str | None = None
    scheduled_for: datetime | None = None
    clinic_id: int | None = None
    slot_id: int | None = None
    visit_type: str = Field(default="clinic", pattern="^(clinic|video)$")
    video_url: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    notes: str | None = None


class AppointmentResponse(AppointmentCreate):
    id: int
    status: str
    requested_at: datetime
    clinic: ClinicResponse | None = None
    slot: AppointmentSlotResponse | None = None
    triage_summary: AppointmentTriageSummary | None = None
