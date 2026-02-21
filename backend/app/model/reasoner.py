from __future__ import annotations

from typing import Protocol

from app.schemas.triage import TriageLevel


class Reasoner(Protocol):
    def reason(
        self, query: str, contexts: list[str], triage_level: TriageLevel
    ) -> str: ...


class StubReasoner:
    def _extract_citations(self, contexts: list[str]) -> list[str]:
        citations: list[str] = []
        for context in contexts:
            first_line = context.splitlines()[0].strip()
            if first_line and first_line not in citations:
                citations.append(first_line)
            if len(citations) >= 2:
                break
        return citations

    def reason(self, query: str, contexts: list[str], triage_level: TriageLevel) -> str:
        if not contexts:
            return (
                f"Triage level: {triage_level}. No medical references were retrieved."
            )

        citations = self._extract_citations(contexts)
        if not citations:
            return f"Triage level: {triage_level}. Retrieved supporting context."

        joined_citations = "; ".join(citations)
        return (
            f"Triage level: {triage_level}. Supporting references: {joined_citations}."
        )
