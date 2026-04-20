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
            if triage_level == "high":
                return "Your symptoms need urgent care right away. Please go to an emergency room or call emergency services."
            elif triage_level == "medium":
                return "You should see a doctor soon, preferably today. Your symptoms need professional assessment."
            else:
                return "Monitor your symptoms. See a doctor if things get worse or don't improve."

        citations = self._extract_citations(contexts)
        if not citations:
            if triage_level == "high":
                return "Your symptoms are serious. Seek emergency care immediately."
            elif triage_level == "medium":
                return "You need to see a doctor soon about your symptoms."
            else:
                return "Rest and stay hydrated. See a doctor if symptoms don't improve."

        # Return simple explanation based on urgency
        if triage_level == "high":
            return f"Your symptoms suggest a serious condition. You need emergency care right away. Your main concerns: {citations[0]}"
        elif triage_level == "medium":
            return f"Your symptoms need urgent attention. See a doctor soon. Key concern: {citations[0]}"
        else:
            return f"Your symptoms may improve with rest. Monitor yourself. Related: {citations[0]}"


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
            "You are a medical triage assistant helping regular people understand their symptoms. "
            "Use SIMPLE, PLAIN LANGUAGE - explain like you're talking to a non-doctor.\n\n"
            "Write ONE SHORT paragraph (3-4 sentences) explaining:\n"
            "1. What might be happening (in simple terms)\n"
            "2. Why it matters (in simple terms)\n"
            "3. What they should do next\n\n"
            "IMPORTANT:\n"
            "- NO medical jargon\n"
            "- NO Latin terms\n"
            "- Use everyday words\n"
            "- Be brief and clear\n"
            "- Don't say 'diagnosis' or claim certainty\n\n"
            f"Symptoms: {query}\n"
            f"Urgency level: {triage_level}\n\n"
            f"Patient information:\n{patient_block}\n\n"
            f"Medical information:\n{context_text}\n\n"
            "Explain simply:"
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
