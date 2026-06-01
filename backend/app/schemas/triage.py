from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TriageLevel = Literal["low", "medium", "high"]
ConditionLikelihood = Literal[
    "more_likely",
    "more likely",
    "possible",
    "less_likely",
    "less likely",
]


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
    earliest_available_slot: str | None = None
    rating: float | None = None
    recommendation_reason: str | None = None
    distance_km: float | None = None
    specialty_match_reason: str | None = None


class SupportingReference(BaseModel):
    title: str = ""
    source: str = ""
    url: str | None = None
    snippet: str = ""


class SuspectedCondition(BaseModel):
    name: str = ""
    likelihood: ConditionLikelihood = "possible"
    explanation: str = ""


class TriageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    patient_id: int | None = None
    lab_values: list[dict[str, str | None]] = Field(default_factory=list)


class LabValue(BaseModel):
    lab_name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None


class LabPdfExtractionResponse(BaseModel):
    filename: str
    values: list[LabValue] = Field(default_factory=list)
    warning: str = (
        "Automated lab extraction may be imperfect. Confirm values before relying "
        "on them clinically."
    )


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    options: list[str] | None = None


class TriageResponse(BaseModel):
    triage_level: TriageLevel
    urgency_level: TriageLevel
    confidence_score: float = 1.0
    needs_clarification: bool = False
    urgency_label: str = ""
    urgency_reason: str = ""
    summary: str = ""
    clinical_summary: str = ""
    simple_reasoning: str = ""
    plain_language_explanation: str = ""
    patient_friendly_explanation: str = ""
    actions: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    recommended_specialty: str | None = None
    specialty_reason: str = ""
    suspected_condition: str | None = None
    suspected_conditions: list[SuspectedCondition] = Field(default_factory=list)
    supporting_references: list[SupportingReference] = Field(default_factory=list)
    suggested_doctors: list[DoctorSuggestion] = Field(default_factory=list)
    history_used: bool = False
    disclaimer: str = ""
    questions: list[ClarificationQuestion] = Field(default_factory=list)


class ClarificationResponse(BaseModel):
    needs_clarification: bool
    original_query: str
    confidence_score: float
    questions: list[ClarificationQuestion]
    triage_result: TriageResponse | None = None


class ClarificationAnswer(BaseModel):
    question_id: str
    answer: str


class ClarificationRequest(BaseModel):
    original_query: str
    answers: list[ClarificationAnswer]
    patient_id: int | None = None


class TriageAssessmentResponse(TriageResponse):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    appointment_id: int | None = None
    query_text: str
    created_at: datetime


class ReasonerCondition(BaseModel):
    name: str = ""
    explanation: str = ""
    likelihood: ConditionLikelihood = "possible"


class ClinicalFeatures(BaseModel):
    chief_complaint: str | None = None
    symptoms: list[str] = Field(default_factory=list)
    body_systems: list[str] = Field(default_factory=list)
    onset: Literal["sudden", "recent", "longstanding", "unknown"] = "unknown"
    duration: str | None = None
    severity: Literal["mild", "moderate", "severe", "unknown"] = "unknown"
    progression: Literal["worsening", "improving", "unknown"] = "unknown"
    red_flags_present: list[str] = Field(default_factory=list)
    red_flags_denied: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    missing_critical_details: list[str] = Field(default_factory=list)


class StructuredReasoningOutput(BaseModel):
    urgency_level: TriageLevel = "low"
    clinical_summary: str = ""
    patient_friendly_explanation: str = ""
    possible_conditions: list[ReasonerCondition] = Field(default_factory=list)
    recommended_specialty: str | None = None
    recommended_actions: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    clinical_features: ClinicalFeatures | None = None


class RejectedSpecialty(BaseModel):
    specialty: str = ""
    reason: str = ""


class SpecialtyAdjudicationOutput(BaseModel):
    final_specialty: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    rejected_specialties: list[RejectedSpecialty] = Field(default_factory=list)
    relevant_reference_titles: list[str] = Field(default_factory=list)
