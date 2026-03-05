from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    reason: str = Field(min_length=1)
    notes: str | None = None
    scheduled_for: datetime | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    notes: str | None = None


class AppointmentResponse(AppointmentCreate):
    id: int
    status: str
    requested_at: datetime
