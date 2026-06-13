from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class VisitCreate(BaseModel):
    patient_id: int
    doctor_id: int | None = None
    appointment_id: int | None = None
    symptoms: str = Field(min_length=1)
    vitals: dict[str, str] | None = None
    diagnosis: str | None = None
    notes: str | None = None
    prescriptions: str | None = None
    attachments: list[str] | None = None


class VisitResponse(VisitCreate):
    id: int
    appointment_id: int | None = None
    created_at: datetime
