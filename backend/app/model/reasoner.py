from __future__ import annotations

import os
from typing import Protocol

import httpx

from app.schemas.triage import TriageLevel


class Reasoner(Protocol):
    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
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

    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> str:
        if not contexts:
            context_note = (
                " Patient history context was included." if patient_context else ""
            )
            return (
                f"Triage level: {triage_level}. "
                f"No medical references were retrieved.{context_note}"
            )

        citations = self._extract_citations(contexts)
        if not citations:
            return f"Triage level: {triage_level}. Retrieved supporting context."

        joined_citations = "; ".join(citations)
        return (
            f"Triage level: {triage_level}. Supporting references: {joined_citations}."
        )


class OllamaReasoner:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip(
            "/"
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4")
        self.timeout_seconds = timeout_seconds
        self._fallback = StubReasoner()

    def ping(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.host}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> str:
        context_text = (
            "\n\n".join(contexts[:3]) if contexts else "No retrieved context."
        )
        patient_block = patient_context or "No patient history provided."
        prompt = (
            "You are a medical triage assistant. "
            "Return one concise paragraph with: risk rationale, key warning signs, "
            "and recommended next action. Avoid diagnosis certainty.\n\n"
            f"Triage level: {triage_level}\n"
            f"Query: {query}\n\n"
            f"Patient context:\n{patient_block}\n\n"
            f"Knowledge context:\n{context_text}\n\n"
            "Output format: Summary: <text>"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
            body = response.json()
            generated = str(body.get("response", "")).strip()
            if generated:
                return generated
        except Exception:
            pass

        return self._fallback.reason(
            query,
            contexts,
            triage_level,
            patient_context=patient_context,
        )
