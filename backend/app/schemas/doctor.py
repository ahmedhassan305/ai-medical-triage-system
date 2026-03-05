from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DoctorProfileUpsert(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    specialty: str = Field(min_length=1, max_length=120)
    clinic: str = Field(min_length=1, max_length=200)


class DoctorProfileResponse(DoctorProfileUpsert):
    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime
