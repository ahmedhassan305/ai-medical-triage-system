from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import httpx

from app.schemas.triage import (
    ClinicalFeatures,
    SpecialtyAdjudicationOutput,
    StructuredReasoningOutput,
    TriageLevel,
)
from app.services.exceptions import TriageSystemUnavailable
from app.services.specialties import allowed_specialties_prompt, canonicalize_specialty

logger = logging.getLogger(__name__)


class SpecialtyAdjudicator(Protocol):
    def adjudicate(
        self,
        *,
        query: str,
        triage_level: TriageLevel,
        reasoning: StructuredReasoningOutput,
        clinical_features: ClinicalFeatures,
        reference_contexts: list[str],
        patient_context: str | None = None,
    ) -> SpecialtyAdjudicationOutput: ...


class StubSpecialtyAdjudicator:
    """Small deterministic fallback for tests or unavailable LLM.

    Production specialty accuracy should come from OllamaSpecialtyAdjudicator.
    This fallback intentionally uses only broad structured body-system signals
    and valid LLM specialty names; it does not maintain a large symptom map.
    """

    _BODY_SYSTEM_SPECIALTIES: dict[str, str] = {
        "respiratory": "Pulmonology",
        "cardiac": "Cardiology",
        "gastrointestinal": "Gastroenterology",
        "musculoskeletal": "Orthopedics",
        "neurologic": "Neurology",
        "skin": "Dermatology",
        "mental_health": "Psychiatry",
        "eye": "Ophthalmology",
        "ent": "ENT",
    }

    def adjudicate(
        self,
        *,
        query: str,
        triage_level: TriageLevel,
        reasoning: StructuredReasoningOutput,
        clinical_features: ClinicalFeatures,
        reference_contexts: list[str],
        patient_context: str | None = None,
    ) -> SpecialtyAdjudicationOutput:
        systems = set(clinical_features.body_systems)
        red_flags = set(clinical_features.red_flags_present)

        if "cardiac" in systems and "possible heart emergency" in red_flags:
            specialty = "Cardiology"
            reason = "Structured features indicate a possible heart emergency."
        else:
            specialty = None
            reason = ""
            for system, mapped_specialty in self._BODY_SYSTEM_SPECIALTIES.items():
                if system in systems:
                    specialty = mapped_specialty
                    reason = (
                        "LLM specialty adjudicator was unavailable; used broad "
                        f"structured body-system signal: {system}."
                    )
                    break

        if specialty is None:
            specialty = canonicalize_specialty(reasoning.recommended_specialty)
            reason = (
                "LLM specialty adjudicator was unavailable; kept the valid "
                "initial LLM specialty."
                if specialty
                else "LLM specialty adjudicator was unavailable; used fallback."
            )

        return SpecialtyAdjudicationOutput(
            final_specialty=specialty or "Internal Medicine",
            confidence=0.4 if specialty else 0.2,
            reasoning=reason,
            relevant_reference_titles=[],
        )


class OllamaSpecialtyAdjudicator:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.host = (host or os.getenv("OLLAMA_HOST", "http://localhost:11434")).rstrip(
            "/"
        )
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
        self.timeout_seconds = timeout_seconds

    def ping(self) -> bool:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.host}/api/tags")
                response.raise_for_status()
            return True
        except Exception:
            return False

    def adjudicate(
        self,
        *,
        query: str,
        triage_level: TriageLevel,
        reasoning: StructuredReasoningOutput,
        clinical_features: ClinicalFeatures,
        reference_contexts: list[str],
        patient_context: str | None = None,
    ) -> SpecialtyAdjudicationOutput:
        prompt = self._build_prompt(
            query=query,
            triage_level=triage_level,
            reasoning=reasoning,
            clinical_features=clinical_features,
            reference_contexts=reference_contexts,
            patient_context=patient_context,
        )
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {"temperature": 0.0},
                    },
                )
                response.raise_for_status()
            raw = str(response.json().get("response", "")).strip()
            logger.info("specialty_adjudicator_raw_json=%s", raw)
            parsed = _parse_adjudication_payload(raw)
            if parsed and parsed.final_specialty:
                return parsed
            logger.warning("specialty_adjudicator_parse_failed raw=%s", raw[:1000])
            raise TriageSystemUnavailable(
                "The triage AI system is unresponsive right now. Please try again shortly."
            )
        except TriageSystemUnavailable:
            raise
        except Exception as exc:
            logger.exception("specialty_adjudicator_failed no_keyword_fallback=true")
            raise TriageSystemUnavailable() from exc

    def _build_prompt(
        self,
        *,
        query: str,
        triage_level: TriageLevel,
        reasoning: StructuredReasoningOutput,
        clinical_features: ClinicalFeatures,
        reference_contexts: list[str],
        patient_context: str | None,
    ) -> str:
        possible_conditions = [
            {
                "name": condition.name,
                "likelihood": condition.likelihood,
                "explanation": condition.explanation,
            }
            for condition in reasoning.possible_conditions[:3]
        ]
        reference_block = (
            "\n\n".join(reference_contexts[:3])
            if reference_contexts
            else "No retrieved references."
        )
        return (
            "You are a medical specialty adjudicator for a triage system.\n"
            "Your only job is to choose the best final doctor specialty. "
            "Do not decide urgency and do not diagnose with certainty.\n\n"
            "Use clinical reasoning, not keyword matching. Consider the whole "
            "case: symptoms, follow-up answers, possible conditions, body "
            "systems, denied warning signs, patient context, and reference "
            "relevance.\n\n"
            "Allowed final specialties, exactly as written:\n"
            f"{allowed_specialties_prompt()}\n\n"
            "Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "final_specialty": "one allowed specialty",\n'
            '  "confidence": 0.0,\n'
            '  "reasoning": "brief explanation of why this specialty fits best",\n'
            '  "rejected_specialties": [\n'
            '    {"specialty": "specialty considered", "reason": "why rejected"}\n'
            "  ],\n"
            '  "relevant_reference_titles": ["reference title that truly supports the case"]\n'
            "}\n\n"
            "Important adjudication principles:\n"
            "- Choose exactly one allowed specialty. Never invent another specialty.\n"
            "- The initial specialty is only a suggestion; reject it if the "
            "clinical picture supports another allowed specialty better.\n"
            "- Risk factors alone, such as smoking, do not justify switching "
            "to Cardiology without a heart-pattern presentation.\n"
            "- Breathing/lung presentations such as fever with trouble breathing, "
            "wheezing, cough, pneumonia, bronchitis, asthma/COPD flare, pleurisy, "
            "or chest tightness with breathing symptoms usually belong to "
            "Pulmonology unless the case clearly has a heart-attack pattern.\n"
            "- Heart-attack pattern means evidence such as crushing/heavy chest "
            "pressure, sweating, pain spreading to arm or jaw, exertional chest "
            "pain relieved by rest, dangerous palpitations, fainting with cardiac "
            "features, or known acute coronary concern.\n"
            "- Back, joint, bone, muscle, strain, sprain, and non-emergency spine "
            "pain usually belong to Orthopedics. Spine symptoms with bladder/bowel "
            "loss or major neurologic deficit may belong to Neurosurgery.\n"
            "- General, vague, multi-system, metabolic, diabetes-like, blood "
            "pressure, kidney, pregnancy, or unclear cases may belong to Internal "
            "Medicine or Family Medicine depending on specificity.\n"
            "- Mark reference titles relevant only if they match the main likely "
            "condition/body system, not merely a shared word such as fever.\n\n"
            f"Patient symptoms/follow-up text:\n{query}\n\n"
            f"Current urgency level, for context only:\n{triage_level}\n\n"
            f"Initial LLM recommended specialty:\n{reasoning.recommended_specialty}\n\n"
            f"Clinical summary:\n{reasoning.clinical_summary}\n\n"
            "Possible conditions from the reasoner:\n"
            f"{json.dumps(possible_conditions, ensure_ascii=False, indent=2)}\n\n"
            "Structured clinical features:\n"
            f"{clinical_features.model_dump_json(indent=2)}\n\n"
            f"Patient context:\n{patient_context or 'No patient context.'}\n\n"
            f"Retrieved references:\n{reference_block}\n\n"
            "Now choose the final specialty."
        )


def _parse_adjudication_payload(raw_text: str) -> SpecialtyAdjudicationOutput | None:
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
        parsed = SpecialtyAdjudicationOutput.model_validate(payload)
    except Exception:
        return None

    parsed.final_specialty = canonicalize_specialty(parsed.final_specialty)
    parsed.rejected_specialties = [
        rejected
        for rejected in parsed.rejected_specialties
        if canonicalize_specialty(rejected.specialty)
    ][:5]
    parsed.relevant_reference_titles = parsed.relevant_reference_titles[:5]
    return parsed
