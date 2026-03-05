from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PatientProfileUpsert(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    age: int = Field(ge=0, le=130)
    sex: str = Field(min_length=1, max_length=20)
    smoker: bool = False
    alcoholic: bool = False
    chronic_conditions: list[str] = Field(default_factory=list)


class PatientProfileResponse(PatientProfileUpsert):
    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime
