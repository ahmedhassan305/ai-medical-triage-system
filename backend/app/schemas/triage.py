from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TriageLevel = Literal["low", "medium", "high"]


class TriageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    patient_id: int | None = None


class TriageSource(BaseModel):
    doc_id: str
    chunk_id: str
    source: str
    title: str
    url: str
    score: float = 0.0


class TriageDecision(BaseModel):
    heuristic_level: TriageLevel
    embedding_level: TriageLevel
    llm_level: TriageLevel | None = None
    final_level: TriageLevel
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1, max_length=2000)


class ReasonerOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    risk_reasoning: str = Field(min_length=1, max_length=4000)
    recommended_action: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    red_flags: list[str] = Field(default_factory=list)
    suggested_level: TriageLevel | None = None


class TriageResponse(BaseModel):
    triage_level: TriageLevel
    summary: str
    actions: list[str]
    disclaimer: str
    history_used: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    risk_reasoning: str
    recommended_action: str
    red_flags: list[str] = Field(default_factory=list)
    sources: list[TriageSource] = Field(default_factory=list)
    decision: TriageDecision
    triage_session_id: int | None = None


class TriageHistoryItem(BaseModel):
    id: int
    query: str
    triage_level: TriageLevel
    confidence: float = Field(ge=0.0, le=1.0)
    history_used: bool
    patient_id: int | None = None
    created_at: datetime


class TriageHistoryPage(BaseModel):
    items: list[TriageHistoryItem]
    total: int
    limit: int
    offset: int


class TriageDetail(BaseModel):
    id: int
    query: str
    patient_id: int | None = None
    user_id: int | None = None
    created_at: datetime
    result: TriageResponse
