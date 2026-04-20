from typing import Literal

from pydantic import BaseModel, Field

TriageLevel = Literal["low", "medium", "high"]


class DoctorSuggestion(BaseModel):
    id: int
    full_name: str
    specialty: str
    clinic: str


class TriageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    patient_id: int | None = None


class TriageResponse(BaseModel):
    triage_level: TriageLevel
    summary: str
    simple_reasoning: str
    plain_language_explanation: str
    actions: list[str]
    recommended_specialty: str | None = None
    suspected_condition: str | None = None
    suggested_doctors: list[DoctorSuggestion] = []
    disclaimer: str
    history_used: bool = False
