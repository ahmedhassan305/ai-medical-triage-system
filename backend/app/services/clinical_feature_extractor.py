from __future__ import annotations

import json
import logging
import os
from typing import Protocol

import httpx

from app.schemas.triage import ClinicalFeatures
from app.services.exceptions import TriageSystemUnavailable

logger = logging.getLogger(__name__)

_ALLOWED_BODY_SYSTEMS = {
    "cardiac",
    "respiratory",
    "neurologic",
    "gastrointestinal",
    "musculoskeletal",
    "skin",
    "mental_health",
    "ent",
    "eye",
    "general",
}

_BODY_SYSTEM_ALIASES = {
    "mental health": "mental_health",
    "psych": "mental_health",
    "psychiatric": "mental_health",
    "gi": "gastrointestinal",
    "digestive": "gastrointestinal",
    "pulmonary": "respiratory",
    "lung": "respiratory",
    "heart": "cardiac",
    "neuro": "neurologic",
    "orthopedic": "musculoskeletal",
    "orthopaedic": "musculoskeletal",
}


class ClinicalFeatureExtractor(Protocol):
    def extract(
        self,
        *,
        query: str,
        local_features: ClinicalFeatures,
        patient_context: str | None = None,
    ) -> ClinicalFeatures: ...


class StubClinicalFeatureExtractor:
    """Development/test extractor: keep deterministic local features."""

    def extract(
        self,
        *,
        query: str,
        local_features: ClinicalFeatures,
        patient_context: str | None = None,
    ) -> ClinicalFeatures:
        return local_features


class OllamaClinicalFeatureExtractor:
    """LLM extractor that reads meaning before the main triage reasoner runs."""

    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 75.0,
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

    def extract(
        self,
        *,
        query: str,
        local_features: ClinicalFeatures,
        patient_context: str | None = None,
    ) -> ClinicalFeatures:
        prompt = self._build_prompt(
            query=query,
            local_features=local_features,
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
                        "options": {"temperature": 0.0, "num_predict": 700},
                    },
                )
                response.raise_for_status()
            raw = str(response.json().get("response", "") or "").strip()
            logger.info("clinical_feature_extractor_raw_json=%s", raw)
            parsed = _parse_feature_payload(raw)
            if parsed is not None:
                return parsed
            logger.warning("clinical_feature_extractor_parse_failed raw=%s", raw[:1000])
            raise TriageSystemUnavailable()
        except TriageSystemUnavailable:
            raise
        except Exception as exc:
            logger.exception(
                "clinical_feature_extractor_failed no_keyword_fallback=true"
            )
            raise TriageSystemUnavailable() from exc

    def _build_prompt(
        self,
        *,
        query: str,
        local_features: ClinicalFeatures,
        patient_context: str | None,
    ) -> str:
        example = {
            "chief_complaint": "main symptom in simple words or null",
            "symptoms": ["normalized symptom explicitly stated or strongly implied"],
            "body_systems": ["one or more allowed body systems"],
            "onset": "sudden|recent|longstanding|unknown",
            "duration": None,
            "severity": "mild|moderate|severe|unknown",
            "progression": "worsening|improving|unknown",
            "red_flags_present": [],
            "red_flags_denied": [],
            "risk_factors": [],
            "missing_critical_details": ["specific missing detail, if important"],
        }
        return (
            "You extract structured clinical features for a medical triage system. "
            "Do not diagnose and do not choose a specialty. Read the patient's "
            "language for meaning, including slang, misspellings, and simple "
            "phrasing. Return ONLY valid JSON with this exact shape:\n"
            "{\n"
            '  "chief_complaint": "plain clinical concept or null",\n'
            '  "symptoms": ["normalized symptom"],\n'
            '  "body_systems": ["cardiac|respiratory|neurologic|'
            "gastrointestinal|musculoskeletal|skin|mental_health|ent|"
            'eye|general"],\n'
            '  "onset": "sudden|recent|longstanding|unknown",\n'
            '  "duration": "brief free-text duration or null",\n'
            '  "severity": "mild|moderate|severe|unknown",\n'
            '  "progression": "worsening|improving|unknown",\n'
            '  "red_flags_present": ["normalized red flag"],\n'
            '  "red_flags_denied": ["normalized denied warning sign"],\n'
            '  "risk_factors": ["risk factor"],\n'
            '  "missing_critical_details": ['
            '"missing detail that could change urgency or routing"]\n'
            "}\n\n"
            "Rules:\n"
            "- Extract features from meaning, not exact keyword matching.\n"
            "- The format template is only a shape guide. Never copy its values.\n"
            "- Use everyday normalized symptom names such as 'breathing difficulty', "
            "'abdominal pain', 'chest discomfort', 'back pain', 'weakness'.\n"
            "- Preserve denied symptoms or warning signs ONLY when the patient "
            "clearly denies them.\n"
            "- If chest pain is not mentioned, do not place chest pain in "
            "red_flags_denied.\n"
            "- If duration is not stated, set duration to null.\n"
            "- If worsening or improvement is not stated, set progression to unknown.\n"
            "- If severity is not stated or strongly implied, set severity to "
            "unknown.\n"
            "- Do not invent symptoms, timing, severity, denied symptoms, risk "
            "factors, or red flags.\n"
            "- If a local safety feature below contains an obvious emergency "
            "sign, keep it.\n"
            "- Keep missing_critical_details focused; ask only for details that would "
            "change urgency, likely condition, or specialty.\n"
            "- Avoid medical jargon in free-text values.\n\n"
            "Format template JSON, not case content:\n"
            f"{json.dumps(example, indent=2)}\n\n"
            f"Patient text:\n{query}\n\n"
            "Local rule-based safety extraction, for backup context only:\n"
            f"{local_features.model_dump_json(indent=2)}\n\n"
            f"Patient context, if any:\n{patient_context or 'No patient context.'}\n\n"
            "Now return the structured clinical features JSON."
        )


def _parse_feature_payload(raw_text: str) -> ClinicalFeatures | None:
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
        parsed = ClinicalFeatures.model_validate(payload)
    except Exception:
        return None

    parsed.body_systems = _normalize_body_systems(parsed.body_systems)
    parsed.symptoms = _clean_list(parsed.symptoms)
    parsed.red_flags_present = _clean_list(parsed.red_flags_present)
    parsed.red_flags_denied = _clean_list(parsed.red_flags_denied)
    parsed.risk_factors = _clean_list(parsed.risk_factors)
    parsed.missing_critical_details = _clean_list(parsed.missing_critical_details)
    return parsed


def _clean_list(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        cleaned.append(item)
        seen.add(key)
    return cleaned


def _normalize_body_systems(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value or "").strip().lower().replace("-", "_")
        item = _BODY_SYSTEM_ALIASES.get(item, item)
        if item not in _ALLOWED_BODY_SYSTEMS or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return normalized or ["general"]
