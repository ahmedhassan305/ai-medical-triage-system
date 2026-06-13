from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Specialty = Literal[
    "Cardiology",
    "Neurology",
    "Neurosurgery",
    "Internal Medicine",
    "Gastroenterology",
    "Dermatology",
    "Psychiatry",
    "Ophthalmology",
    "Orthopedics",
    "ENT",
    "Pediatrics",
    "Family Medicine",
    "Pulmonology",
]

TriageLevel = Literal["low", "medium", "high"]
CaseType = Literal[
    "specialty",
    "urgency",
    "clarification",
    "grounding",
    "history",
    "robustness",
]
Difficulty = Literal["easy", "medium", "hard", "controversial"]
LanguageStyle = Literal["clinical", "common_language", "noisy", "typo_heavy"]


class ExpectedResult(BaseModel):
    specialty: Specialty
    acceptable_specialties: list[Specialty] = Field(min_length=1)
    urgency: TriageLevel
    needs_clarification: bool

    @model_validator(mode="after")
    def ensure_primary_specialty_is_acceptable(self) -> "ExpectedResult":
        if self.specialty not in self.acceptable_specialties:
            raise ValueError(
                "expected.specialty must also appear in acceptable_specialties"
            )
        return self


class NullableExpectedResult(BaseModel):
    specialty: Specialty | None = None
    acceptable_specialties: list[Specialty] = []
    urgency: TriageLevel | None = None
    needs_clarification: bool | None = None

    @model_validator(mode="after")
    def ensure_consistency(self) -> "NullableExpectedResult":
        if self.specialty is not None and self.specialty not in self.acceptable_specialties:
            raise ValueError(
                "clarification.expected_after_answers.specialty must also appear "
                "in acceptable_specialties"
            )
        return self


class HistoryEntry(BaseModel):
    symptoms: str = Field(min_length=1)
    diagnosis: str | None = None
    notes: str | None = None


class PatientContext(BaseModel):
    age: int | None = Field(default=None, ge=0, le=130)
    sex: Literal["Male", "Female"] | None = None
    smoker: bool | None = None
    alcoholic: bool | None = None
    chronic_conditions: list[str] = []
    history: list[HistoryEntry] = []


class ClarificationAnswer(BaseModel):
    question_id: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class ClarificationSpec(BaseModel):
    expected_questions: list[str] = []
    answers: list[ClarificationAnswer] = []
    expected_after_answers: NullableExpectedResult


class GroundingSpec(BaseModel):
    facts_present: list[str] = []
    facts_absent: list[str] = []
    must_not_invent: list[str] = []


class Metadata(BaseModel):
    primary_specialty_group: Specialty
    difficulty: Difficulty
    language_style: LanguageStyle
    tags: list[str] = []
    rationale: str = Field(min_length=1)


class TriageEvalCase(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$")
    case_type: CaseType
    query: str = Field(min_length=1)
    expected: ExpectedResult
    patient_context: PatientContext
    clarification: ClarificationSpec
    grounding: GroundingSpec
    metadata: Metadata
