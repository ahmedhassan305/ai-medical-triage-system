from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TriageLevel = Literal["low", "medium", "high"]
ConditionLikelihood = Literal["more_likely", "possible", "less_likely"]


class DoctorSuggestion(BaseModel):
    id: int
    full_name: str
    specialty: str
    clinic: str
    area: str | None = None
    city: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    booking_url: str | None = None


class SupportingReference(BaseModel):
    title: str
    source: str
    url: str | None = None
    snippet: str


class SuspectedCondition(BaseModel):
    name: str
    likelihood: ConditionLikelihood
    explanation: str


class ReasonerCondition(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=500)


class StructuredReasoningOutput(BaseModel):
    urgency_level: TriageLevel
    clinical_summary: str = Field(min_length=1)
    patient_friendly_explanation: str = Field(min_length=1)
    possible_conditions: list[ReasonerCondition] = Field(default_factory=list)
    recommended_specialty: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class TriageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    patient_id: int | None = None


class TriageResponse(BaseModel):
    triage_level: TriageLevel
    urgency_level: TriageLevel
    urgency_label: str
    urgency_reason: str | None = None
    summary: str
    clinical_summary: str
    simple_reasoning: str
    plain_language_explanation: str
    patient_friendly_explanation: str
    actions: list[str]
    recommended_actions: list[str]
    red_flags: list[str] = Field(default_factory=list)
    recommended_specialty: str | None = None
    specialty_reason: str | None = None
    suspected_condition: str | None = None
    suspected_conditions: list[SuspectedCondition] = Field(default_factory=list)
    suggested_doctors: list[DoctorSuggestion] = Field(default_factory=list)
    supporting_references: list[SupportingReference] = Field(default_factory=list)
    disclaimer: str
    history_used: bool = False


class TriageAssessmentResponse(TriageResponse):
    id: int
    patient_id: int
    appointment_id: int | None = None
    query_text: str
    created_at: datetime
