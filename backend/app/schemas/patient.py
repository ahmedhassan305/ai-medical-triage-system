from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


def normalize_patient_sex(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "male":
        return "Male"
    if normalized == "female":
        return "Female"
    raise ValueError("Sex must be either Male or Female.")


class PatientProfileUpsert(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    age: int = Field(ge=0, le=130)
    sex: str = Field(min_length=1, max_length=20)
    national_id: str | None = Field(default=None)
    current_governorate: str | None = Field(default=None, max_length=120)
    smoker: bool = False
    alcoholic: bool = False
    chronic_conditions: list[str] = Field(default_factory=list)

    @field_validator("national_id", "current_governorate")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value: str) -> str:
        return normalize_patient_sex(value)


class ManagedPatientProfileCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    sex: str = Field(min_length=1, max_length=20)
    national_id: str = Field(min_length=14, max_length=14)
    current_governorate: str | None = Field(default=None, max_length=120)
    smoker: bool = False
    alcoholic: bool = False
    chronic_conditions: list[str] = Field(default_factory=list)

    @field_validator("national_id", "current_governorate")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, value: str) -> str:
        return normalize_patient_sex(value)


class PatientProfileResponse(PatientProfileUpsert):
    id: int
    user_id: int | None = None
    date_of_birth: date | None = None
    inferred_governorate_code: str | None = None
    inferred_governorate: str | None = None
    created_at: datetime
    updated_at: datetime
