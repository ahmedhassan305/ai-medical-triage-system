from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import httpx

from app.patient_symptoms import PATIENT_SYMPTOM_KEYWORDS
from app.schemas.triage import (
    ReasonerCondition,
    StructuredReasoningOutput,
    TriageLevel,
)

logger = logging.getLogger(__name__)

HIGH_RISK_TERMS: tuple[str, ...] = (
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "stroke",
    "seizure",
    "unconscious",
    "severe bleeding",
    "overdose",
    "suicidal",
    "throat closing",
)

MEDIUM_RISK_TERMS: tuple[str, ...] = (
    "fever",
    "vomiting",
    "dehydration",
    "fracture",
    "burn",
    "infection",
    "migraine",
)


class Reasoner(Protocol):
    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> StructuredReasoningOutput: ...


class StubReasoner:
    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> StructuredReasoningOutput:
        possible_conditions = _guess_conditions(query)
        red_flags = _extract_red_flags(query)
        explanation = _fallback_explanation(
            triage_level, possible_conditions, red_flags
        )
        actions = _fallback_actions(triage_level)
        specialty = _fallback_specialty(possible_conditions)

        if patient_context and "Relevant history" in patient_context:
            explanation = (
                f"{explanation} Your recent health history was considered while "
                "reviewing this complaint."
            )

        return StructuredReasoningOutput(
            urgency_level=triage_level,
            clinical_summary=_fallback_clinical_summary(
                triage_level,
                possible_conditions,
                query,
            ),
            patient_friendly_explanation=explanation,
            possible_conditions=possible_conditions,
            recommended_specialty=specialty,
            recommended_actions=actions,
            red_flags=red_flags,
        )


class OllamaReasoner:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 180.0,
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
            return True
        except Exception:
            return False

    def reason(
        self,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None = None,
    ) -> StructuredReasoningOutput:
        prompt = self._build_prompt(
            query=query,
            contexts=contexts,
            triage_level=triage_level,
            patient_context=patient_context,
        )
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.host}/api/generate", json=payload)
                response.raise_for_status()
            generated = str(response.json().get("response", "")).strip()
            logger.info("reasoner_raw_json=%s", generated)
            parsed = _parse_reasoner_payload(generated)
            if parsed is not None:
                return parsed
            logger.warning("reasoner_parse_failed raw=%s", generated[:1000])
        except Exception:
            logger.exception("reasoner_generation_failed fallback=stub")

        return self._fallback.reason(
            query,
            contexts,
            triage_level,
            patient_context=patient_context,
        )

    def _build_prompt(
        self,
        *,
        query: str,
        contexts: list[str],
        triage_level: TriageLevel,
        patient_context: str | None,
    ) -> str:
        example_payload = {
            "urgency_level": "medium",
            "clinical_summary": (
                "Respiratory symptoms with fever could reflect an acute lower "
                "respiratory infection. The patient reports productive cough and "
                "elevated temperature, consistent with pneumonia or acute "
                "bronchitis based on retrieved medical literature."
            ),
            "patient_friendly_explanation": (
                "Your symptoms may be related to a chest or breathing infection. "
                "Because you have fever and cough, it would be safer to speak "
                "with a doctor soon rather than waiting several days."
            ),
            "possible_conditions": [
                {
                    "name": "Pneumonia",
                    "explanation": (
                        "Fever with persistent productive cough and respiratory "
                        "findings can fit this pattern."
                    ),
                },
                {
                    "name": "Acute Bronchitis",
                    "explanation": (
                        "Fever and productive cough are classic findings. "
                        "Usually self-limited but medical review is prudent."
                    ),
                },
            ],
            "recommended_specialty": "Internal Medicine",
            "recommended_actions": [
                "Arrange a same-day medical review if symptoms are worsening.",
                "Seek urgent help if breathing becomes difficult.",
            ],
            "red_flags": ["trouble breathing", "blue lips", "coughing up blood"],
        }
        context_text = (
            "\n\n".join(contexts[:3]) if contexts else "No retrieved evidence."
        )
        patient_block = patient_context or "No patient history provided."
        return (
            "You are a careful medical triage assistant with expertise in "
            "clinical reasoning. "
            "You do not give a confirmed diagnosis but provide careful "
            "clinical assessment. "
            "Use plain, reassuring language for non-doctors. "
            "Use the retrieved medical evidence when it is relevant. "
            "IMPORTANT: Explicitly identify and name specific medical "
            "conditions from your clinical reasoning.\n\n"
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "urgency_level": "low|medium|high",\n'
            '  "clinical_summary": "detailed clinician-style summary with "'
            '"specific condition names identified from reasoning",\n'
            '  "patient_friendly_explanation": "simple explanation for the patient",\n'
            '  "possible_conditions": [\n'
            '    {"name": "specific condition name", "explanation": "why it "'
            '"may fit based on symptoms", "likelihood": "more likely|"'
            '"possible|less likely"}\n'
            "  ],\n"
            '  "recommended_specialty": "specialty name or null",\n'
            '  "recommended_actions": ["action 1", "action 2"],\n'
            '  "red_flags": ["warning sign 1", "warning sign 2"]\n'
            "}\n\n"
            "Rules:\n"
            "- Treat retrieved evidence as supporting material, not as truth.\n"
            "- Use retrieved evidence ONLY when it clearly matches the "
            "patient's symptoms and context.\n"
            "- If a retrieved article is weakly related, irrelevant, or "
            "conflicts with the symptoms, ignore it.\n"
            "- Do not list a condition only because it appears in retrieved "
            "evidence; the patient's symptoms must fit.\n"
            "- If evidence is insufficient, say what is uncertain and keep "
            "the differential broad.\n"
            "- Gastroenterology is ONLY for: vomiting blood, blood in stool, "
            "jaundice/yellow skin, liver disease, severe abdominal pain, "
            "colonoscopy-related, bowel disease. Weight loss, fatigue, "
            "general stomach discomfort = Internal Medicine.\n"
            "- recommended_specialty MUST be exactly one of: Cardiology, "
            "Neurology, Neurosurgery, Internal Medicine, Gastroenterology, "
            "Dermatology, Psychiatry, Ophthalmology, Orthopedics, ENT, "
            "Pediatrics, Family Medicine. No other values are allowed.\n"
            "- possible_conditions must contain 1 to 3 specific medical conditions.\n"
            ""
            "- ALWAYS include the most likely specific condition name (e.g., "
            "'Pneumonia', 'Myocardial infarction', 'Meningitis').\n"
            "- Use exact medical terminology in condition names for extraction "
            "by downstream systems.\n"
            "- Use wording such as 'possible condition' or 'may be related to'.\n"
            "- Do not overstate certainty.\n"
            "- Keep patient_friendly_explanation to 3 or 4 short sentences.\n"
            "- If symptoms sound dangerous, set urgency_level to high.\n"
            "- Be explicit about clinical reasoning - name the specific "
            "conditions you are considering.\n\n"
            "Example JSON:\n"
            f"{json.dumps(example_payload, indent=2)}\n\n"
            f"Symptoms: {query}\n"
            f"Safety baseline urgency: {triage_level}\n\n"
            f"Patient context:\n{patient_block}\n\n"
            f"Retrieved medical evidence:\n{context_text}\n"
            "Note: Do NOT mention scores, percentages, or source rankings in "
            "your response. Do not copy the example explanation verbatim.\n"
            "\nNow analyze this case and provide detailed clinical reasoning "
            "with specific condition names."
        )


def _parse_reasoner_payload(raw_text: str) -> StructuredReasoningOutput | None:
    candidate = raw_text.strip()
    if not candidate:
        return None

    if not candidate.startswith("{"):
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = candidate[start : end + 1]

    try:
        payload = json.loads(candidate)
        return StructuredReasoningOutput.model_validate(payload)
    except Exception:
        return None


def _guess_conditions(query: str) -> list[ReasonerCondition]:
    lowered = query.lower()
    conditions: list[ReasonerCondition] = []
    seen: set[str] = set()
    for keyword, condition_text in PATIENT_SYMPTOM_KEYWORDS:
        if keyword not in lowered:
            continue
        for condition_name in _split_condition_text(condition_text):
            normalized = condition_name.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            conditions.append(
                ReasonerCondition(
                    name=condition_name,
                    explanation="This possibility matches symptoms you described.",
                )
            )
            if len(conditions) >= 3:
                return conditions
    return conditions


def _split_condition_text(condition_text: str) -> list[str]:
    return [item.strip() for item in condition_text.split("/") if item.strip()]


def _extract_red_flags(query: str) -> list[str]:
    lowered = query.lower()
    matches = [term for term in HIGH_RISK_TERMS if term in lowered]
    if matches:
        return matches[:3]
    return [term for term in MEDIUM_RISK_TERMS if term in lowered][:2]


def _fallback_explanation(
    triage_level: TriageLevel,
    possible_conditions: list[ReasonerCondition],
    red_flags: list[str],
) -> str:
    if triage_level == "high":
        return (
            "Your symptoms could reflect a serious problem and should be checked "
            "urgently. Please seek emergency care now, especially if the symptoms "
            "are getting worse."
        )
    if triage_level == "medium":
        if possible_conditions:
            return (
                f"Your symptoms may be related to {possible_conditions[0].name}. "
                "This does not look trivial, so arranging medical review soon would "
                "be the safer step."
            )
        return (
            "Your symptoms do not sound like a minor issue. It would be safer to "
            "speak with a doctor soon rather than waiting."
        )

    explanation = (
        "Your symptoms may be related to a less urgent condition, but they still "
        "deserve attention if they continue or get worse."
    )
    if red_flags:
        explanation += " If warning signs develop, seek urgent care sooner."
    return explanation


def _fallback_clinical_summary(
    triage_level: TriageLevel,
    possible_conditions: list[ReasonerCondition],
    query: str,
) -> str:
    query_text = query.strip().rstrip(".")
    if possible_conditions:
        top_condition = possible_conditions[0].name
        if triage_level == "high":
            return (
                f"{query_text.capitalize()} is concerning for {top_condition}. "
                "Immediate evaluation is advised."
            )
        if triage_level == "medium":
            return (
                f"{query_text.capitalize()} may be related to {top_condition}. "
                "It is best to seek medical review soon."
            )
        return (
            f"{query_text.capitalize()} may be related to {top_condition}. "
            "Monitor symptoms and follow up if they persist or worsen."
        )

    if triage_level == "high":
        return (
            f"{query_text.capitalize()} is concerning and may reflect a "
            "serious medical issue. "
            "Seek immediate care."
        )
    if triage_level == "medium":
        return (
            f"{query_text.capitalize()} suggests a condition worth reviewing soon. "
            "Arrange care if symptoms continue or worsen."
        )
    return (
        f"{query_text.capitalize()} appears less urgent but should be monitored. "
        "Follow up if symptoms do not improve."
    )


def _fallback_actions(triage_level: TriageLevel) -> list[str]:
    if triage_level == "high":
        return [
            "Seek emergency care immediately.",
            "Call local emergency services if symptoms escalate.",
        ]
    if triage_level == "medium":
        return [
            "Arrange urgent medical review today or as soon as possible.",
            "Seek faster care if symptoms worsen or new warning signs appear.",
        ]
    return [
        "Rest, stay hydrated, and monitor how you feel.",
        "Book a routine review if symptoms persist or you are worried.",
    ]


def _fallback_specialty(
    possible_conditions: list[ReasonerCondition],
) -> str | None:
    if not possible_conditions:
        return None

    lowered = " ".join(condition.name.lower() for condition in possible_conditions)
    if any(token in lowered for token in ("heart", "cardiac", "coronary")):
        return "Cardiology"
    if any(
        token in lowered
        for token in ("asthma", "copd", "pneumonia", "bronchitis", "lung")
    ):
        return "Pulmonology"
    if any(
        token in lowered
        for token in ("stomach", "appendicitis", "gastritis", "gerd", "bowel")
    ):
        return "Gastroenterology"
    if any(
        token in lowered
        for token in ("migraine", "stroke", "meningitis", "neuropathy", "vertigo")
    ):
        return "Neurology"
    if any(token in lowered for token in ("fracture", "sprain", "arthritis")):
        return "Orthopedics"
    return "General Practice"
