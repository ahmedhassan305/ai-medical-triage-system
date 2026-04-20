from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.patient import normalize_patient_sex

RoleType = Literal["patient", "doctor", "admin"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RoleType = "patient"
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    national_id: str | None = Field(default=None)
    sex: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode="after")
    def require_patient_identity(self) -> "RegisterRequest":
        if self.role != "patient":
            return self

        missing_fields = [
            field_name
            for field_name in ("full_name", "national_id", "sex")
            if not getattr(self, field_name)
        ]
        if missing_fields:
            joined = ", ".join(missing_fields)
            raise ValueError(
                f"Patient registration requires the following fields: {joined}."
            )
        return self

    @model_validator(mode="after")
    def validate_patient_sex(self) -> "RegisterRequest":
        if self.role != "patient" or not self.sex:
            return self
        try:
            normalize_patient_sex(self.sex)
        except ValueError as e:
            raise ValueError(str(e)) from e
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: RoleType
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: RoleType
