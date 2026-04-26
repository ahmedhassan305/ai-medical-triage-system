from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import httpx

from app.schemas.triage import ReasonerOutput, TriageLevel

logger = logging.getLogger(__name__)

MAX_CONTEXT_ITEMS = 2
MAX_CONTEXT_CHARS = 450
MAX_PATIENT_CONTEXT_CHARS = 600


class Reasoner(Protocol):
    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> ReasonerOutput: ...


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
    ) -> ReasonerOutput:
        if not contexts:
            context_note = (
                " Patient history context was included." if patient_context else ""
            )
            return ReasonerOutput(
                summary=(
                    "Triage level: "
                    f"{triage_level}. No medical references were retrieved."
                    f"{context_note}"
                ),
                risk_reasoning=(
                    "The provisional severity is "
                    f"{triage_level} based on current rules."
                ),
                recommended_action=(
                    "Follow the recommended actions for the reported severity "
                    "and seek care if symptoms worsen."
                ),
                confidence=0.58,
                red_flags=[],
                suggested_level=triage_level,
            )

        citations = self._extract_citations(contexts)
        if not citations:
            return ReasonerOutput(
                summary=f"Triage level: {triage_level}. Retrieved supporting context.",
                risk_reasoning=(
                    "The provisional severity is "
                    f"{triage_level} and retrieved references support "
                    "additional review."
                ),
                recommended_action=(
                    "Use the recommended actions for this severity and review "
                    "the retrieved sources."
                ),
                confidence=0.62,
                red_flags=[],
                suggested_level=triage_level,
            )

        joined_citations = "; ".join(citations)
        return ReasonerOutput(
            summary=(
                "Triage level: "
                f"{triage_level}. Supporting references: {joined_citations}."
            ),
            risk_reasoning=(
                f"Severity remains {triage_level} after checking the "
                "retrieved references."
            ),
            recommended_action=(
                "Review the cited material and escalate to urgent or emergency "
                "care if symptoms intensify."
            ),
            confidence=0.66,
            red_flags=[],
            suggested_level=triage_level,
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
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout_seconds = timeout_seconds
        self._fallback = StubReasoner()

    def ping(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.host}/api/tags")
                response.raise_for_status()
            payload = response.json()
            models = payload.get("models", [])
            names = {
                str(item.get("name", "")).strip()
                for item in models
                if isinstance(item, dict)
            }
            if self.model in names:
                return True
            prefix = f"{self.model}:"
            return any(name.startswith(prefix) for name in names)
        except Exception:
            return False

    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> ReasonerOutput:
        context_text = self._compact_contexts(contexts)
        patient_block = self._compact_patient_context(patient_context)
        prompt = (
            "You are a medical triage assistant.\n"
            "Return valid JSON only with these keys: "
            "summary, risk_reasoning, recommended_action, confidence, "
            "red_flags, suggested_level.\n"
            "Keep the response cautious and concise.\n"
            "Do not claim a definitive diagnosis.\n"
            "Use lowercase for suggested_level: low, medium, or high.\n"
            "Confidence must be between 0 and 1.\n\n"
            f"Provisional triage level from rules: {triage_level}\n"
            f"Query: {query}\n\n"
            f"Patient context:\n{patient_block}\n\n"
            f"Knowledge context:\n{context_text}\n\n"
            "Return JSON only."
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 180,
                "num_ctx": 2048,
            },
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
            body = response.json()
            generated = str(body.get("response", "")).strip()
            if generated:
                parsed = self._parse_output(generated)
                if parsed is not None:
                    return parsed
                logger.warning(
                    "ollama_reasoner_invalid_json_response preview=%s",
                    generated[:300].replace("\n", " "),
                )
        except Exception:
            logger.exception("ollama_reasoner_request_failed")

        return self._fallback.reason(
            query,
            contexts,
            triage_level,
            patient_context=patient_context,
        )

    def _parse_output(self, generated: str) -> ReasonerOutput | None:
        candidate = generated.strip()
        if not candidate.startswith("{"):
            start = candidate.find("{")
            end = candidate.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            candidate = candidate[start : end + 1]

        try:
            payload = json.loads(candidate)
            suggested_level = payload.get("suggested_level")
            if isinstance(suggested_level, str):
                payload["suggested_level"] = suggested_level.strip().lower()
            return ReasonerOutput.model_validate(payload)
        except Exception:
            return None

    def _compact_contexts(self, contexts: list[str]) -> str:
        if not contexts:
            return "No retrieved context."

        compacted: list[str] = []
        for item in contexts[:MAX_CONTEXT_ITEMS]:
            compacted.append(self._truncate(item, MAX_CONTEXT_CHARS))
        return "\n\n".join(compacted)

    def _compact_patient_context(self, patient_context: str | None) -> str:
        if not patient_context:
            return "No patient history provided."
        return self._truncate(patient_context, MAX_PATIENT_CONTEXT_CHARS)

    def _truncate(self, value: str, limit: int) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip() + "..."
