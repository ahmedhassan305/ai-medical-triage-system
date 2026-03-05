from typing import Literal

from pydantic import BaseModel, Field

TriageLevel = Literal["low", "medium", "high"]


class TriageRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    patient_id: int | None = None


class TriageResponse(BaseModel):
    triage_level: TriageLevel
    summary: str
    actions: list[str]
    disclaimer: str
    history_used: bool = False
