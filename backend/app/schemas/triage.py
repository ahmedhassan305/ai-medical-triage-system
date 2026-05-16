from typing import Any, Literal

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
    actions: list[str] = []
    recommended_actions: list[str] = []
    red_flags: list[str] = []
    recommended_specialty: str | None = None
    specialty_reason: str = ""
    suspected_condition: str | None = None
    suspected_conditions: list[dict[str, Any]] = []
    supporting_references: list[dict[str, Any]] = []  # keys: title, source, url, snippet
    suggested_doctors: list[DoctorSuggestion] = []
    history_used: bool = False
    disclaimer: str = ""
    questions: list["ClarificationQuestion"] = []


class ClarificationQuestion(BaseModel):
    id: str
    question: str
    options: list[str] | None = None


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


class ReasonerCondition(BaseModel):
    name: str
    explanation: str
    likelihood: Literal["more likely", "possible", "less likely"] = "possible"


class StructuredReasoningOutput(BaseModel):
    urgency_level: TriageLevel
    clinical_summary: str = ""
    patient_friendly_explanation: str = ""
    possible_conditions: list[ReasonerCondition] = []
    recommended_specialty: str | None = None
    recommended_actions: list[str] = []
    red_flags: list[str] = []

