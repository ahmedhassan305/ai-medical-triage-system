from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DoctorProfile, PatientProfile
from app.model.reasoner import OllamaReasoner, Reasoner, StubReasoner
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.reranker import rerank_retrieved_chunks
from app.rag.retriever import Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.schemas.triage import (
    ClarificationQuestion,
    ClinicalFeatures,
    DoctorSuggestion,
    ReasonerCondition,
    SpecialtyAdjudicationOutput,
    TriageLevel,
    TriageResponse,
)
from app.services.clarification_service import (
    get_clarification_questions,
    needs_clarification,
)
from app.services.clinical_feature_extractor import (
    ClinicalFeatureExtractor,
    OllamaClinicalFeatureExtractor,
    StubClinicalFeatureExtractor,
)
from app.services.clinical_features import (
    assess_urgency_from_features,
    extract_clinical_features,
)
from app.services.exceptions import TriageSystemUnavailable
from app.services.patient_context import PatientContextProvider
from app.services.specialties import (
    TRIAGE_SPECIALTIES,
    canonicalize_specialty,
)
from app.services.specialty_adjudicator import (
    OllamaSpecialtyAdjudicator,
    SpecialtyAdjudicator,
    StubSpecialtyAdjudicator,
)
from app.services.triage_localization import (
    add_arabic_query_hints,
    detect_language,
    localize_questions,
    localize_triage_response,
)

logger = logging.getLogger(__name__)

TRIAGE_LEVEL_RANK: dict[TriageLevel, int] = {"low": 0, "medium": 1, "high": 2}
MIN_REASONER_RAG_SCORE = 0.48
MIN_SUPPORTING_REFERENCE_SCORE = 0.5
RAG_CANDIDATE_MULTIPLIER = 6
REASONER_RAG_LIMIT = 5
VALID_SPECIALTIES = TRIAGE_SPECIALTIES

SUBSPECIALTY_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "Orthopedics": {
        "knee": ("knee", "acl", "meniscus", "patella"),
        "shoulder": ("shoulder", "rotator cuff"),
        "hand": ("hand", "wrist", "finger", "carpal"),
        "arm": ("arm", "elbow"),
        "foot_ankle": ("foot", "ankle", "heel"),
        "spine": ("spine", "spinal", "back", "neck", "disc"),
        "fracture": ("fracture", "broken", "trauma"),
        "sports": ("sports", "sport injury", "athlete"),
        "joint": ("joint", "arthritis", "replacement"),
    },
    "Pulmonology": {
        "asthma": ("asthma", "wheez", "bronchospasm"),
        "infection": ("pneumonia", "bronchitis", "cough", "infection"),
        "copd": ("copd", "emphysema", "smoker", "smoking"),
        "endoscopy": ("bronchoscopy", "endoscopy"),
    },
    "Gastroenterology": {
        "liver": ("liver", "hepat", "jaundice"),
        "endoscopy": ("endoscopy", "colonoscopy", "scope"),
        "bowel": ("bowel", "colon", "ibd", "crohn", "ulcerative"),
        "stomach": ("stomach", "abdominal", "reflux", "gastritis"),
    },
    "Cardiology": {
        "catheterization": ("catheter", "angiography", "stent"),
        "vascular": ("vascular", "angiology"),
        "rhythm": ("arrhythmia", "rhythm", "palpitation"),
    },
    "Neurology": {
        "headache": ("headache", "migraine"),
        "stroke": ("stroke", "weakness", "numbness"),
        "seizure": ("seizure", "epilepsy"),
    },
}

HIGH_RISK_KEYWORDS: tuple[str, ...] = (
    # Minimal deterministic safety floor: only obvious emergency phrases.
    # Broader urgency reasoning should come from structured features + LLM.
    "can't breathe",
    "cannot breathe",
    "not breathing",
    "barely speak",
    "blue lips",
    "blue fingertips",
    "chest pain with shortness of breath",
    "chest pain and shortness of breath",
    "chest pressure with sweating",
    "crushing chest pain",
    "pain spreading to jaw",
    "pain spreading to arm",
    "heart attack",
    "face drooping",
    "slurred speech",
    "one-sided weakness",
    "seizure",
    "unconscious",
    "unresponsive",
    "severe bleeding",
    "bleeding a lot",
    "won't stop bleeding",
    "overdose",
    "suicidal",
    "want to hurt myself",
    "throat closing",
    "tongue swelling",
)

MEDIUM_RISK_KEYWORDS: tuple[str, ...] = ()

HIGH_RISK_FEATURE_FLAGS: frozenset[str] = frozenset(
    {
        "breathing distress",
        "possible heart emergency",
        "stroke-like symptoms",
        "seizure or loss of consciousness",
        "major bleeding",
        "self-harm risk",
        "possible serious allergy",
        "possible serious liver disease",
        "loss of bladder or bowel control",
    }
)


def _match_any(query: str, keywords: tuple[str, ...]) -> bool:
    q = query.lower()
    return any(k in q for k in keywords)


def _classify(query: str) -> TriageLevel:
    level: TriageLevel = "low"
    if _match_any(query, HIGH_RISK_KEYWORDS):
        level = "high"
    elif _match_any(query, MEDIUM_RISK_KEYWORDS):
        level = "medium"
    return level


def _max_triage_level(*levels: TriageLevel) -> TriageLevel:
    return max(levels, key=lambda level: TRIAGE_LEVEL_RANK[level])


def _reasoner_high_is_supported(
    *,
    safety_level: TriageLevel,
    feature_level: TriageLevel,
    summary,
    trusted_features,
) -> bool:
    if safety_level == "high" or feature_level == "high":
        return True

    if HIGH_RISK_FEATURE_FLAGS.intersection(trusted_features.red_flags_present):
        return True

    summary_features = getattr(summary, "clinical_features", None)
    summary_red_flags_present = set(
        getattr(summary_features, "red_flags_present", []) or []
    )
    return bool(HIGH_RISK_FEATURE_FLAGS.intersection(summary_red_flags_present))


def _reconcile_reasoner_urgency(
    *,
    safety_level: TriageLevel,
    feature_level: TriageLevel,
    reasoner_level: TriageLevel,
    summary,
    trusted_features,
) -> tuple[TriageLevel, bool]:
    if reasoner_level != "high":
        return _max_triage_level(safety_level, feature_level, reasoner_level), False

    if _reasoner_high_is_supported(
        safety_level=safety_level,
        feature_level=feature_level,
        summary=summary,
        trusted_features=trusted_features,
    ):
        return "high", False

    # Keep the case cautious, but do not let an unsupported LLM-only escalation
    # become the final answer without stronger evidence.
    return _max_triage_level(safety_level, feature_level, "medium"), True


def _safety_floor(query: str, age: int | None = None) -> TriageLevel:
    return _classify_with_age(query, age)


def _build_actions(triage_level: TriageLevel) -> list[str]:
    if triage_level == "high":
        actions = [
            "Seek emergency care now.",
            "Call local emergency services if symptoms are severe or worsening.",
        ]
    elif triage_level == "medium":
        actions = [
            "Consider urgent care or a same-day clinic visit.",
            "Seek care sooner if symptoms worsen or new symptoms appear.",
        ]
    else:
        actions = [
            "Consider rest, hydration, and over-the-counter options if appropriate.",
            "Seek care if symptoms persist, worsen, or you are concerned.",
        ]

    return actions


def _filter_chunks_for_reasoner(chunks: list, min_score: float) -> list:
    if not chunks:
        return []

    filtered = [chunk for chunk in chunks if getattr(chunk, "score", 0.0) >= min_score]
    if filtered:
        return filtered

    best_chunk = max(chunks, key=lambda chunk: getattr(chunk, "score", 0.0))
    best_score = getattr(best_chunk, "score", 0.0)
    if best_score >= 0.38:
        return [best_chunk]
    return []


def _filter_supporting_reference_chunks(chunks: list) -> list:
    filtered = [
        chunk
        for chunk in chunks
        if getattr(chunk, "score", 0.0) >= MIN_SUPPORTING_REFERENCE_SCORE
    ]
    return filtered or chunks


def _filter_reference_chunks_by_conditions(chunks: list, conditions: list) -> list:
    condition_names = [
        str(getattr(condition, "name", "") or "").strip().lower()
        for condition in conditions
    ]
    condition_names = [name for name in condition_names if name]
    if not condition_names:
        return chunks

    filtered = []
    for chunk in chunks:
        title = str(getattr(chunk, "title", "") or "").strip().lower()
        if not title:
            continue
        if any(name in title or title in name for name in condition_names):
            filtered.append(chunk)

    return filtered


def _filter_reference_chunks_by_features(
    chunks: list,
    clinical_features: ClinicalFeatures,
) -> list:
    """Keep fallback references that support multiple extracted symptom signals."""
    symptom_terms: dict[str, tuple[str, ...]] = {
        "breathing difficulty": (
            "breathing difficulty",
            "difficulty breathing",
            "shortness of breath",
            "trouble breathing",
        ),
        "chest discomfort": ("chest discomfort", "chest pain", "chest tightness"),
        "wheezing": ("wheezing", "wheez"),
    }
    extracted_symptoms = [
        symptom.strip().lower()
        for symptom in clinical_features.symptoms
        if symptom and symptom.strip()
    ]
    if not extracted_symptoms:
        return []

    matched_chunks = []
    for chunk in chunks:
        searchable = " ".join(
            str(value or "").lower()
            for value in (
                getattr(chunk, "title", ""),
                getattr(chunk, "text", ""),
                getattr(chunk, "source", ""),
            )
        )
        matched_symptoms = 0
        for symptom in extracted_symptoms:
            terms = symptom_terms.get(symptom, (symptom,))
            if any(term in searchable for term in terms):
                matched_symptoms += 1
        if matched_symptoms >= 2:
            matched_chunks.append(chunk)

    return matched_chunks


def _sanitize_condition_explanations(query: str, conditions: list) -> None:
    lowered = query.lower()
    has_fever = "fever" in lowered or "temperature" in lowered
    has_cough = "cough" in lowered
    has_wheeze = "wheez" in lowered
    has_breathing = any(
        term in lowered
        for term in (
            "shortness of breath",
            "short of breath",
            "difficulty breathing",
            "trouble breathing",
            "can't breathe",
            "cannot breathe",
        )
    )
    has_chest_tightness = "chest tight" in lowered
    has_liver_pattern = any(
        term in lowered
        for term in (
            "jaundice",
            "yellow eyes",
            "yellow skin",
            "abdominal swelling",
            "swollen abdomen",
            "ascites",
            "dark urine",
        )
    )

    for condition in conditions:
        name = str(getattr(condition, "name", "") or "").strip()
        explanation = str(getattr(condition, "explanation", "") or "")
        normalized_name = name.lower()
        if has_liver_pattern and (
            normalized_name == "liver disease" or "liver disease" in normalized_name
        ):
            condition.explanation = (
                "Jaundice or yellow eyes with abdominal swelling and dark urine "
                "can indicate a serious liver or bile-flow problem."
            )
            continue
        if not (has_breathing or has_wheeze or has_cough):
            explanation_sentences = re.split(r"(?<=[.!?])\s+", explanation.strip())
            explanation = (
                " ".join(
                    sentence
                    for sentence in explanation_sentences
                    if "alpha-1" not in sentence.lower()
                    and "antitrypsin" not in sentence.lower()
                ).strip()
                or explanation
            )
            condition.explanation = explanation
        explanation_lower = explanation.lower()
        mentions_unstated_fever = "fever" in explanation_lower and not has_fever
        mentions_unstated_cough = "cough" in explanation_lower and not has_cough
        if not (mentions_unstated_fever or mentions_unstated_cough):
            continue

        if "bronch" in normalized_name and (
            has_wheeze or has_breathing or has_chest_tightness
        ):
            condition.explanation = (
                "Chest tightness, wheezing, and shortness of breath can fit an "
                "airway irritation or bronchitis-like pattern, but more details "
                "are needed."
            )
        elif "pneum" in normalized_name and has_breathing:
            condition.explanation = (
                "Shortness of breath can occur with pneumonia, but the absence "
                "of stated fever or cough makes this less certain."
            )
        else:
            condition.explanation = (
                "This remains a possible condition based on the described "
                "symptom pattern, but the current query does not include every "
                "classic feature."
            )


def _condition_supported_for_display(
    query: str,
    clinical_features: ClinicalFeatures,
    condition,
    age: int | None = None,
) -> bool:
    lowered = query.lower()
    name = str(getattr(condition, "name", "") or "").strip().lower()
    symptoms = set(clinical_features.symptoms)
    red_flags = set(clinical_features.red_flags_present)

    has_fever = "fever" in lowered or "temperature" in lowered
    has_cough = "cough" in lowered
    has_fatigue = "fatigue" in lowered or "tired" in lowered
    has_wheeze = "wheez" in lowered or "wheezing" in symptoms
    has_breathing = "breathing difficulty" in symptoms
    has_chest_discomfort = "chest discomfort" in symptoms
    has_jaundice = "jaundice" in symptoms
    has_abdominal_swelling = "abdominal swelling" in symptoms
    has_dark_urine = "dark urine" in symptoms
    has_liver_pattern = has_jaundice or has_dark_urine or has_abdominal_swelling
    pediatric_context = (age is not None and age < 1) or any(
        term in lowered
        for term in ("newborn", "infant", "baby", "few weeks old", "new baby")
    )
    has_gi_bleeding = any(
        term in lowered
        for term in (
            "vomiting blood",
            "blood in vomit",
            "black stool",
            "black stools",
            "bloody stool",
            "blood in stool",
            "throwing up blood",
        )
    )
    has_cirrhosis_context = any(
        term in lowered
        for term in ("cirrhosis", "known liver disease", "portal hypertension")
    )
    has_liver_failure_context = any(
        term in lowered
        for term in (
            "confusion",
            "very sleepy",
            "drowsy",
            "bleeding",
            "easy bruising",
            "severe abdominal pain",
        )
    )
    has_exposure_context = any(
        term in lowered
        for term in (
            "chemical",
            "mold",
            "bird",
            "dust",
            "radiation",
            "immunotherapy",
            "chemotherapy",
            "hot tub",
            "farm",
            "work exposure",
        )
    )
    has_heart_pattern = bool(
        red_flags.intersection({"possible heart emergency"})
        or any(
            term in lowered
            for term in (
                "crushing chest",
                "chest pressure",
                "sweating",
                "pain spreading to arm",
                "pain spreading to jaw",
                "palpitation",
                "fainted",
                "fainting",
            )
        )
    )

    if "pneumonitis" in name:
        return has_exposure_context or sum([has_fever, has_cough, has_fatigue]) >= 2

    if "biliary atresia" in name:
        return pediatric_context and has_liver_pattern

    if "alpha-1" in name or "antitrypsin" in name:
        return has_breathing or has_wheeze or has_cough

    if "varices" in name:
        return has_gi_bleeding or has_cirrhosis_context

    if "acute liver failure" in name:
        return has_liver_pattern and has_liver_failure_context

    if "alcoholic hepatitis" in name or "alcohol-associated hepatitis" in name:
        return has_liver_pattern

    if "liver" in name or "hepat" in name or "cirrhosis" in name:
        return has_liver_pattern

    if "pneumonia" in name:
        return has_fever or has_cough or (has_breathing and not has_wheeze)

    if any(
        cardiac in name
        for cardiac in (
            "myocarditis",
            "pericarditis",
            "acute coronary",
            "myocardial infarction",
            "heart attack",
        )
    ):
        return has_chest_discomfort and has_heart_pattern

    if "asthma" in name or "bronchospasm" in name:
        return has_wheeze or has_breathing

    if "bronch" in name:
        return has_cough or has_wheeze or has_breathing

    return True


def _display_conditions(
    query: str,
    clinical_features: ClinicalFeatures,
    conditions: list,
    age: int | None = None,
) -> list:
    filtered = [
        condition
        for condition in conditions
        if _condition_supported_for_display(query, clinical_features, condition, age)
    ]
    if filtered:
        return filtered[:3]

    symptoms = set(clinical_features.symptoms)
    if "jaundice" in symptoms or "dark urine" in symptoms:
        return [
            ReasonerCondition(
                name="Liver disease",
                explanation=(
                    "Jaundice or yellow eyes with dark urine and abdominal "
                    "swelling can indicate a serious liver or bile-flow problem."
                ),
            )
        ]

    return conditions[:1]


def _sanitize_summary_text(summary_text: str, display_conditions: list) -> str:
    allowed_condition_names = {
        str(getattr(condition, "name", "") or "").strip().lower()
        for condition in display_conditions
    }
    allowed_condition_names = {name for name in allowed_condition_names if name}
    blocked_condition_names = {
        "myocarditis",
        "pericarditis",
        "acute coronary syndrome",
        "myocardial infarction",
        "heart attack",
        "pneumonitis",
        "esophageal varices",
        "varices",
        "acute liver failure",
        "biliary atresia",
        "alpha-1-antitrypsin deficiency",
        "alpha-1",
        "bronchospasm",
        "asthma-like",
        "asthma exacerbation",
    } - allowed_condition_names

    sentences = re.split(r"(?<=[.!?])\s+", summary_text.strip())
    kept: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if "orthopedics" in lowered and "current symptoms" in lowered:
            continue
        if any(name in lowered for name in blocked_condition_names):
            continue
        kept.append(sentence)

    cleaned = " ".join(kept).strip()
    if "liver disease" in allowed_condition_names and (
        not cleaned or cleaned.lower().startswith(("however", "but", "without further"))
    ):
        return (
            "Jaundice or yellow eyes with abdominal swelling and dark urine can "
            "indicate a serious liver or bile-flow problem and needs urgent "
            "medical assessment."
        )

    return cleaned or summary_text


def _preview_text(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    preview = ""
    for sentence in sentences:
        candidate = f"{preview} {sentence}".strip()
        if len(candidate) > limit:
            break
        preview = candidate
    return preview or cleaned[:limit].rsplit(" ", 1)[0].strip()


def _patient_facing_specialty_reason(reason: str, specialty: str | None) -> str:
    lowered = reason.lower()
    if "adjudicator" in lowered or "llm" in lowered or "skipped" in lowered:
        return (
            "Recommended after reviewing the symptoms and likely body system: "
            f"{specialty or 'the most relevant specialty'}."
        )
    return reason


def _patient_facing_red_flags(flags: list[str], triage_level: TriageLevel) -> list[str]:
    if triage_level == "high":
        return flags

    danger_terms = (
        "blue lips",
        "blue fingertips",
        "barely speak",
        "coughing up blood",
        "fainting",
        "confusion",
        "severe breathing",
        "worsening breathing",
        "throat closing",
    )
    filtered: list[str] = []
    for flag in flags:
        lowered = flag.lower()
        if any(term in lowered for term in danger_terms):
            filtered.append(flag)
    return filtered


def _format_reasoner_context(chunk) -> str:
    header = f"({chunk.source}) {chunk.title}"
    if chunk.url:
        header = f"{header} - {chunk.url}"
    return f"{header}\n[score: {chunk.score:.4f}]\n{chunk.text}"


def _normalize_recommended_specialty(
    specialty: str | None,
    query: str,
    triage_level: TriageLevel,
    *,
    possible_conditions: list[str] | None = None,
    body_systems: list[str] | None = None,
    red_flags_present: list[str] | None = None,
) -> str:
    """Final fallback only.

    The production specialty decision is made by SpecialtyAdjudicator. This
    function deliberately avoids large condition/symptom keyword maps and only
    keeps enough broad routing to return a safe valid specialty if the LLM
    adjudicator is unavailable or returns an invalid value.
    """
    if specialty:
        import re as _re

        candidate = _re.split(r" or |and/or|/|,|;", specialty, maxsplit=1)[0].strip()
        candidate = candidate.split("(")[0].strip()
        normalized = canonicalize_specialty(candidate)
        if normalized:
            return normalized

    system_led = _specialty_from_body_systems(
        body_systems or [],
        red_flags_present=red_flags_present or [],
    )
    if system_led:
        return system_led

    lowered_query = query.lower()
    if "heart attack" in lowered_query:
        return "Cardiology"
    if any(term in lowered_query for term in ("baby", "child", "toddler", "infant")):
        return "Pediatrics"
    return "Internal Medicine"


def _specialty_from_body_systems(
    body_systems: list[str],
    *,
    red_flags_present: list[str] | None = None,
) -> str | None:
    systems = set(body_systems)
    red_flags = set(red_flags_present or [])

    if "possible heart emergency" in red_flags:
        return "Cardiology"

    if "respiratory" in systems and "cardiac" in systems:
        if "possible heart emergency" in red_flags:
            return "Cardiology"
        return "Pulmonology"

    if "respiratory" in systems:
        return "Pulmonology"
    if "cardiac" in systems:
        return "Cardiology"
    if "neurologic" in systems:
        return "Neurology"
    if "musculoskeletal" in systems:
        return "Orthopedics"
    if "skin" in systems:
        return "Dermatology"
    if "mental_health" in systems:
        return "Psychiatry"
    if "eye" in systems:
        return "Ophthalmology"
    if "ent" in systems:
        return "ENT"
    if "gastrointestinal" in systems:
        return "Gastroenterology"
    return None


def _merge_llm_features_with_safety(
    llm_features: ClinicalFeatures | None,
    safety_features: ClinicalFeatures,
) -> ClinicalFeatures:
    """Prefer LLM clinical interpretation, preserving deterministic safety flags."""

    if llm_features is None:
        return safety_features

    return ClinicalFeatures(
        chief_complaint=llm_features.chief_complaint or safety_features.chief_complaint,
        symptoms=list(
            dict.fromkeys([*llm_features.symptoms, *safety_features.symptoms])
        ),
        body_systems=list(
            dict.fromkeys([*llm_features.body_systems, *safety_features.body_systems])
        ),
        onset=(
            llm_features.onset
            if llm_features.onset != "unknown"
            else safety_features.onset
        ),
        duration=llm_features.duration or safety_features.duration,
        severity=(
            llm_features.severity
            if llm_features.severity != "unknown"
            else safety_features.severity
        ),
        progression=(
            llm_features.progression
            if llm_features.progression != "unknown"
            else safety_features.progression
        ),
        red_flags_present=list(
            dict.fromkeys(
                [
                    *llm_features.red_flags_present,
                    *safety_features.red_flags_present,
                ]
            )
        ),
        red_flags_denied=list(
            dict.fromkeys(
                [
                    *llm_features.red_flags_denied,
                    *safety_features.red_flags_denied,
                ]
            )
        ),
        risk_factors=list(
            dict.fromkeys([*llm_features.risk_factors, *safety_features.risk_factors])
        ),
        missing_critical_details=llm_features.missing_critical_details
        or safety_features.missing_critical_details,
    )


def _retrieval_query_from_features(
    query: str,
    clinical_features: ClinicalFeatures,
    age_context: str,
) -> str:
    feature_terms = [
        clinical_features.chief_complaint or "",
        *clinical_features.symptoms,
        *clinical_features.body_systems,
        clinical_features.severity if clinical_features.severity != "unknown" else "",
        clinical_features.onset if clinical_features.onset != "unknown" else "",
        clinical_features.duration or "",
        *clinical_features.red_flags_present,
    ]
    feature_text = " ".join(term for term in feature_terms if term)
    return " ".join(part for part in (query, feature_text, age_context) if part).strip()


def _usable_reasoner_questions(
    questions: list[ClarificationQuestion],
    clinical_features: ClinicalFeatures,
) -> list[ClarificationQuestion]:
    if not questions:
        return []

    timing_known = clinical_features.onset != "unknown" or bool(
        clinical_features.duration
    )
    cleaned: list[ClarificationQuestion] = []
    seen: set[str] = set()

    for question in questions:
        question_text = (question.question or "").strip()
        if not question_text:
            continue
        lowered = f"{question.id} {question_text}".lower()
        if timing_known and (
            "when" in lowered
            or "how long" in lowered
            or "duration" in lowered
            or "onset" in lowered
            or "start" in lowered
        ):
            continue
        key = question_text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(question)
        if len(cleaned) >= 3:
            break

    return cleaned


def _adjudication_fast_path(
    *,
    reasoner_specialty: str | None,
    clinical_features,
) -> SpecialtyAdjudicationOutput | None:
    """Skip expensive LLM adjudication when specialty evidence is coherent.

    This is intentionally conservative: it only accepts the reasoner's specialty
    when it is allowed and agrees with the broad structured body-system route.
    Ambiguous or conflict-prone presentations still go to the adjudicator.
    """
    normalized = canonicalize_specialty(reasoner_specialty)
    if not normalized:
        return None

    body_system_specialty = _specialty_from_body_systems(
        clinical_features.body_systems,
        red_flags_present=clinical_features.red_flags_present,
    )
    if body_system_specialty != normalized:
        return None

    systems = set(clinical_features.body_systems)
    red_flags = set(clinical_features.red_flags_present)

    # Keep heart/lung overlap under adjudication unless there is confirmed
    # heart-emergency evidence. This protects the Cardiology/Pulmonology edge.
    if {"respiratory", "cardiac"}.issubset(systems):
        if normalized != "Cardiology" or "possible heart emergency" not in red_flags:
            return None

    return SpecialtyAdjudicationOutput(
        final_specialty=normalized,
        confidence=0.78,
        reasoning=(
            "Skipped specialty adjudicator: the initial LLM specialty agrees "
            "with structured clinical body-system evidence."
        ),
        rejected_specialties=[],
        relevant_reference_titles=[],
    )


def _build_retriever() -> Retriever:
    settings = get_settings()
    if settings.rag_retriever == "stub":
        return StubRetriever()

    data_dir = Path(settings.rag_data_dir)
    if not data_dir.exists() or not data_dir.is_dir():
        logger.warning(
            "rag_retriever_unavailable data_dir_missing=%s fallback=stub",
            data_dir,
        )
        return StubRetriever()

    if settings.rag_retriever == "tfidf":
        try:
            return TfidfRetriever(
                data_dir=str(data_dir),
                max_features=settings.tfidf_max_features,
                ngram_range=(settings.tfidf_ngram_min, settings.tfidf_ngram_max),
            )
        except Exception:
            logger.exception("tfidf_retriever_initialization_failed fallback=stub")
            return StubRetriever()

    if settings.rag_retriever == "embedding":
        try:
            return EmbeddingRetriever(
                data_dir=str(data_dir),
                chunk_size=settings.rag_chunk_size,
                overlap=settings.rag_chunk_overlap,
                top_k=settings.rag_top_k,
            )
        except Exception:
            logger.exception("embedding_retriever_initialization_failed fallback=stub")
            return StubRetriever()

    logger.warning(
        "rag_retriever_unknown value=%s fallback=stub",
        settings.rag_retriever,
    )
    return StubRetriever()


@lru_cache
def get_retriever() -> Retriever:
    return _build_retriever()


def _build_reasoner() -> Reasoner:
    settings = get_settings()
    mode = settings.reasoner_mode

    if mode == "stub":
        logger.info("reasoner_initialized mode=stub model=none")
        return StubReasoner()

    if mode == "ollama":
        reasoner = OllamaReasoner(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
        if reasoner.ping():
            logger.info(
                "reasoner_initialized mode=ollama model=%s host=%s",
                settings.ollama_model,
                settings.ollama_host,
            )
            return reasoner

        logger.error("reasoner_unavailable mode=ollama host=%s", settings.ollama_host)
        raise TriageSystemUnavailable()

    logger.warning("reasoner_mode_unknown value=%s fallback=stub", mode)
    logger.info("reasoner_initialized mode=stub model=none")
    return StubReasoner()


@lru_cache
def get_reasoner() -> Reasoner:
    return _build_reasoner()


def _build_clinical_feature_extractor() -> ClinicalFeatureExtractor:
    settings = get_settings()
    mode = settings.reasoner_mode

    if mode == "ollama":
        extractor = OllamaClinicalFeatureExtractor(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
        if extractor.ping():
            logger.info(
                "clinical_feature_extractor_initialized mode=ollama model=%s host=%s",
                settings.ollama_model,
                settings.ollama_host,
            )
            return extractor

        logger.error(
            "clinical_feature_extractor_unavailable mode=ollama host=%s",
            settings.ollama_host,
        )
        raise TriageSystemUnavailable()

    logger.info("clinical_feature_extractor_initialized mode=stub")
    return StubClinicalFeatureExtractor()


@lru_cache
def get_clinical_feature_extractor() -> ClinicalFeatureExtractor:
    return _build_clinical_feature_extractor()


def _build_specialty_adjudicator() -> SpecialtyAdjudicator:
    settings = get_settings()
    mode = settings.reasoner_mode

    if mode == "ollama":
        adjudicator = OllamaSpecialtyAdjudicator(
            host=settings.ollama_host,
            model=settings.ollama_model,
        )
        if adjudicator.ping():
            logger.info(
                "specialty_adjudicator_initialized mode=ollama model=%s host=%s",
                settings.ollama_model,
                settings.ollama_host,
            )
            return adjudicator

        logger.error(
            "specialty_adjudicator_unavailable mode=ollama host=%s",
            settings.ollama_host,
        )
        raise TriageSystemUnavailable()

    logger.info("specialty_adjudicator_initialized mode=stub")
    return StubSpecialtyAdjudicator()


@lru_cache
def get_specialty_adjudicator() -> SpecialtyAdjudicator:
    return _build_specialty_adjudicator()


def _preload_model() -> None:
    """Preload the LLM model into VRAM on startup."""
    import os as _os

    import httpx as _httpx

    host = _os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = _os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    try:
        logger.info("preloading_model model=%s", model)
        with _httpx.Client(timeout=60.0) as client:
            client.post(
                f"{host}/api/generate",
                json={
                    "model": model,
                    "prompt": "hi",
                    "stream": False,
                    "options": {"num_predict": 1},
                },
            )
        logger.info("model_preloaded model=%s", model)
    except Exception as e:
        logger.warning("model_preload_failed error=%s", e)


def clear_runtime_state() -> None:
    get_retriever.cache_clear()
    get_reasoner.cache_clear()
    get_clinical_feature_extractor.cache_clear()
    get_specialty_adjudicator.cache_clear()


def simplify_reasoning(text: str) -> str:
    """Convert medical jargon to simple language for patients."""
    replacements = {
        "cardiac": "heart",
        "cardiovascular": "heart and blood vessel",
        "respiratory": "breathing",
        "pulmonary": "lung",
        "gastrointestinal": "stomach and digestive",
        "gi": "digestive",
        "neurological": "brain and nerve",
        "dermatological": "skin",
        "musculoskeletal": "bone and muscle",
        "infectious": "infection",
        "endocrine": "hormone",
        "renal": "kidney",
        "hepatic": "liver",
        "hematologic": "blood",
        "immunological": "immune system",
        "psychiatric": "mental health",
        "etiology": "cause",
        "symptomatology": "symptoms",
        "contraindication": "caution or risk",
        "diagnosis": "condition",
        "prognosis": "expected outcome",
        "pathophysiology": "how the disease works",
        "differential diagnosis": "possible conditions",
        "clinical presentation": "signs and symptoms",
        "acute": "sudden start",
        "chronic": "long-term",
        "exacerbation": "getting worse",
        "remission": "improvement",
        "comorbidity": "related health condition",
        "intervention": "treatment",
        "pharmacological": "medication-based",
        "therapeutic": "treatment-related",
        "manifestation": "sign or symptom",
        "sequelae": "complications",
        "prophylactic": "preventive",
    }

    result = text
    for medical, simple in replacements.items():
        result = result.replace(medical, simple)
        result = result.replace(medical.capitalize(), simple.capitalize())

    return result


def get_suspected_condition(
    query: str,
    summary: str,
    rag_context: str = "",
    reasoner_output: object | None = None,
) -> str:
    """Return the LLM's top supported condition, without keyword diagnosis.

    Production condition display should come from the reasoner's explicit
    differential. Keyword scanning is intentionally not used here because it can
    turn incidental words from the query, summary, or RAG references into a
    patient-facing suspected condition.
    """
    if reasoner_output is not None and hasattr(reasoner_output, "possible_conditions"):
        for condition in reasoner_output.possible_conditions or []:
            name = (
                condition.get("name", "")
                if isinstance(condition, dict)
                else getattr(condition, "name", "")
            )
            name = str(name or "").strip()
            if name:
                return name

    return "Unknown condition"


def _get_age_context(age: int | None) -> str:
    """Get age-appropriate clinical context for triage."""
    if age is None:
        return ""

    if age < 1:
        return (
            "NEONATE/INFANT - Critical: Monitor vital signs closely, "
            "fever in infants <3 months is emergency."
        )
    elif age < 5:
        return (
            "TODDLER/PRESCHOOL - High risk: Dehydration, airway compromise, "
            "fever. Watch for lethargy."
        )
    elif age < 13:
        return (
            "CHILD - Consider pediatric norms: Heart rate, respiratory rate, "
            "blood pressure vary by age."
        )
    elif age < 18:
        return (
            "ADOLESCENT - Consider psychosocial factors, contraception "
            "counseling if relevant."
        )
    elif age < 65:
        return "ADULT - Standard adult presentation."
    else:
        return (
            "GERIATRIC - Higher risk: Polypharmacy, atypical presentations, "
            "falls, cognitive changes."
        )


def _classify_with_age(query: str, age: int | None = None) -> TriageLevel:
    """Classify urgency considering age factors."""
    level: TriageLevel = "low"

    if age is not None and age < 5:
        pedi_high_risk = (
            "fever",
            "stridor",
            "drooling",
            "retracting",
            "cyanosis",
            "lethargy",
            "unresponsive",
            "seizure",
            "dehydration",
            "not eating",
            "vomiting",
            "diarrhea for hours",
        )
        if _match_any(query, pedi_high_risk):
            level = "high"

    if age is not None and age >= 65:
        if _match_any(query, HIGH_RISK_KEYWORDS):
            level = "high"
        elif _match_any(query, ("fall", "confusion", "weakness", "dizziness")):
            level = "medium"

    if level == "low":
        if _match_any(query, HIGH_RISK_KEYWORDS):
            level = "high"
        elif _match_any(query, MEDIUM_RISK_KEYWORDS):
            level = "medium"

    return level


def _normalize_location(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _text_matches_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _subspecialty_needs(
    specialty: str,
    query: str,
    clinical_features: ClinicalFeatures | None,
) -> set[str]:
    haystack = " ".join(
        [
            query.lower(),
            " ".join(clinical_features.symptoms if clinical_features else []),
            clinical_features.chief_complaint or "" if clinical_features else "",
        ]
    )
    specialty_map = SUBSPECIALTY_KEYWORDS.get(specialty, {})
    return {
        label
        for label, terms in specialty_map.items()
        if _text_matches_any(haystack, terms)
    }


def _doctor_match_score(
    doc: DoctorProfile,
    *,
    specialty: str,
    subspecialty_needs: set[str],
    patient_location: str | None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if doc.specialty == specialty:
        score += 100.0
        reasons.append("Main specialty matches your case")

    doctor_text = " ".join(
        part
        for part in (
            doc.specialty,
            doc.clinic,
            doc.area or "",
            doc.city or "",
        )
        if part
    ).lower()
    specialty_map = SUBSPECIALTY_KEYWORDS.get(specialty, {})

    matched_subspecialties = [
        label
        for label in subspecialty_needs
        if _text_matches_any(doctor_text, specialty_map.get(label, ()))
    ]
    if matched_subspecialties:
        score += 35.0 + (8.0 * min(len(matched_subspecialties), 3))
        labels = ", ".join(label.replace("_", " ") for label in matched_subspecialties)
        reasons.append(f"Subspecialty fit: {labels}")

    if patient_location:
        patient_location_normalized = _normalize_location(patient_location)
        doctor_city = _normalize_location(doc.city)
        doctor_area = _normalize_location(doc.area)
        if doctor_city and doctor_city == patient_location_normalized:
            score += 18.0
            reasons.append(f"Same governorate/city: {doc.city}")
        elif doctor_area and doctor_area == patient_location_normalized:
            score += 24.0
            reasons.append(f"Same area: {doc.area}")

    if doc.booking_url:
        score += 2.0

    return score, reasons


def get_suggested_doctors(
    db: Session,
    specialty: str,
    *,
    query: str = "",
    clinical_features: ClinicalFeatures | None = None,
    patient_id: int | None = None,
    limit: int = 3,
) -> list[DoctorSuggestion]:
    """Get doctors ranked by specialty, subspecialty wording, and location."""
    if not db:
        return []

    try:
        patient_location: str | None = None
        if patient_id is not None:
            patient = (
                db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
            )
            if patient is not None:
                patient_location = (
                    patient.current_governorate or patient.inferred_governorate
                )

        needs = _subspecialty_needs(specialty, query, clinical_features)
        doctors = (
            db.query(DoctorProfile).filter(DoctorProfile.specialty == specialty).all()
        )

        scored = []
        for doc in doctors:
            score, reasons = _doctor_match_score(
                doc,
                specialty=specialty,
                subspecialty_needs=needs,
                patient_location=patient_location,
            )
            scored.append((score, doc.full_name.lower(), doc.id, doc, reasons))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))

        return [
            DoctorSuggestion(
                id=doc.id,
                full_name=doc.full_name,
                specialty=doc.specialty,
                clinic=doc.clinic,
                area=doc.area,
                city=doc.city,
                source_name=doc.source_name,
                source_url=doc.source_url,
                booking_url=doc.booking_url,
                recommendation_reason=(
                    "; ".join(reasons)
                    if reasons
                    else "Main specialty matches your case"
                ),
                specialty_match_reason=(
                    "; ".join(reasons)
                    if reasons
                    else "Main specialty matches your case"
                ),
            )
            for _score, _name, _id, doc, reasons in scored[:limit]
        ]
    except Exception as e:
        logger.warning(f"Failed to get doctors for specialty {specialty}: {e}")
        return []


def _legacy_get_suggested_doctors(
    db: Session, specialty: str, limit: int = 3
) -> list[DoctorSuggestion]:
    try:
        doctors = (
            db.query(DoctorProfile)
            .filter(DoctorProfile.specialty == specialty)
            .order_by(DoctorProfile.full_name.asc())
            .limit(limit)
            .all()
        )

        return [
            DoctorSuggestion(
                id=doc.id,
                full_name=doc.full_name,
                specialty=doc.specialty,
                clinic=doc.clinic,
            )
            for doc in doctors
        ]
    except Exception as e:
        logger.warning(f"Failed to get doctors for specialty {specialty}: {e}")
        return []


def triage(
    query: str,
    patient_id: int | None = None,
    db: Session | None = None,
    age: int | None = None,
    lab_values: list[dict[str, str | None]] | None = None,
    language: str = "en",
) -> TriageResponse:
    normalized_query = query.strip()
    response_language = detect_language(normalized_query, language)
    extraction_query = add_arabic_query_hints(normalized_query)
    if age is None and patient_id is not None and db is not None:
        patient = (
            db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
        )
        age = patient.age if patient is not None else None
    settings = get_settings()

    patient_context: str | None = None
    history_used = False
    if patient_id is not None and db is not None:
        provider = PatientContextProvider(
            visit_limit=settings.patient_history_visit_limit,
            top_matches=settings.patient_history_top_matches,
        )
        patient_result = provider.build(db, patient_id, extraction_query)
        patient_context = patient_result.context_text
        history_used = patient_result.history_used
        logger.info(
            "triage_history_context_loaded patient_id=%s matches=%s",
            patient_id,
            len(patient_result.matched_visit_ids),
        )
    elif patient_id is not None:
        patient_context = f"Patient ID {patient_id} was provided."
        history_used = True

    if lab_values:
        lab_lines = [
            (
                f"- {value.get('lab_name')}: {value.get('value')}"
                f" {value.get('unit') or ''}".strip()
            )
            for value in lab_values
            if value.get("lab_name") and value.get("value")
        ]
        if lab_lines:
            lab_context = (
                "=== UPLOADED BLOODWORK / LAB VALUES ===\n"
                "Use these confirmed extracted lab values as supporting context. "
                "Do not diagnose from labs alone.\n" + "\n".join(lab_lines)
            )
            patient_context = (
                f"{patient_context}\n\n{lab_context}"
                if patient_context
                else lab_context
            )
            history_used = True

    base_features = extract_clinical_features(extraction_query, age=age)
    safety_level = _max_triage_level(
        _safety_floor(extraction_query, age),
        assess_urgency_from_features(base_features, age=age),
    )
    triage_level = safety_level

    extracted_features = (
        get_clinical_feature_extractor().extract(
            query=extraction_query,
            local_features=base_features,
            patient_context=patient_context,
        )
        if settings.llm_aux_calls
        else None
    )
    pre_reasoner_features = _merge_llm_features_with_safety(
        extracted_features,
        base_features,
    )
    pre_reasoner_feature_level = assess_urgency_from_features(
        pre_reasoner_features,
        age=age,
    )
    triage_level = _max_triage_level(triage_level, pre_reasoner_feature_level)

    age_context = _get_age_context(age)
    retrieval_query = _retrieval_query_from_features(
        normalized_query,
        pre_reasoner_features,
        age_context,
    )
    candidate_top_k = max(
        settings.rag_top_k * RAG_CANDIDATE_MULTIPLIER, settings.rag_top_k
    )
    candidate_chunks = get_retriever().retrieve_chunks(
        retrieval_query,
        top_k=candidate_top_k,
    )
    reranked_chunks = rerank_retrieved_chunks(
        retrieval_query,
        candidate_chunks,
        limit=max(REASONER_RAG_LIMIT, settings.rag_top_k),
    )
    reasoner_chunks = _filter_chunks_for_reasoner(
        reranked_chunks,
        MIN_REASONER_RAG_SCORE,
    )
    chunks = reranked_chunks[: settings.rag_top_k]
    contexts = [_format_reasoner_context(chunk) for chunk in reasoner_chunks]

    summary = get_reasoner().reason(
        normalized_query,
        contexts,
        triage_level,
        patient_context=patient_context,
        clinical_features=pre_reasoner_features,
    )
    _sanitize_condition_explanations(
        normalized_query,
        summary.possible_conditions if hasattr(summary, "possible_conditions") else [],
    )
    clinical_features = _merge_llm_features_with_safety(
        getattr(summary, "clinical_features", None),
        pre_reasoner_features,
    )
    display_conditions = _display_conditions(
        normalized_query,
        clinical_features,
        summary.possible_conditions if hasattr(summary, "possible_conditions") else [],
    )
    feature_level = assess_urgency_from_features(clinical_features, age=age)
    triage_level, unsupported_reasoner_high = _reconcile_reasoner_urgency(
        safety_level=safety_level,
        feature_level=feature_level,
        reasoner_level=summary.urgency_level,
        summary=summary,
        trusted_features=base_features,
    )
    actions = _build_actions(triage_level)

    summary_text = (
        summary.clinical_summary
        if hasattr(summary, "clinical_summary")
        else str(summary)
    )
    summary_text = _sanitize_summary_text(summary_text, display_conditions)
    simple_reasoning = simplify_reasoning(summary_text)
    specialty_adjudication = _adjudication_fast_path(
        reasoner_specialty=getattr(summary, "recommended_specialty", None),
        clinical_features=clinical_features,
    )
    if specialty_adjudication is None:
        if settings.llm_aux_calls:
            specialty_adjudication = get_specialty_adjudicator().adjudicate(
                query=normalized_query,
                triage_level=triage_level,
                reasoning=summary,
                clinical_features=clinical_features,
                reference_contexts=contexts,
                patient_context=patient_context,
            )
        else:
            specialty_adjudication = StubSpecialtyAdjudicator().adjudicate(
                query=normalized_query,
                triage_level=triage_level,
                reasoning=summary,
                clinical_features=clinical_features,
                reference_contexts=contexts,
                patient_context=patient_context,
            )
    recommended_specialty = canonicalize_specialty(
        specialty_adjudication.final_specialty
    ) or _normalize_recommended_specialty(
        (
            summary.recommended_specialty
            if hasattr(summary, "recommended_specialty")
            else None
        ),
        normalized_query,
        triage_level,
        body_systems=clinical_features.body_systems,
        red_flags_present=clinical_features.red_flags_present,
    )
    specialty_reason = (
        specialty_adjudication.reasoning.strip()
        if specialty_adjudication.reasoning
        else (
            "Recommended after reviewing the clinical picture: "
            f"{recommended_specialty}."
        )
    )
    specialty_reason = _patient_facing_specialty_reason(
        specialty_reason,
        recommended_specialty,
    )
    rag_context_str = " ".join(
        f"{getattr(c, 'title', '')} {getattr(c, 'text', '')[:200]}".strip()
        for c in reasoner_chunks
    )
    suspected_condition = (
        str(getattr(display_conditions[0], "name", "") or "").strip()
        if display_conditions
        else get_suspected_condition(
            normalized_query,
            summary_text,
            rag_context_str,
            reasoner_output=summary,
        )
    )

    suggested_doctors = (
        get_suggested_doctors(
            db,
            recommended_specialty,
            query=normalized_query,
            clinical_features=clinical_features,
            patient_id=patient_id,
        )
        if db and recommended_specialty
        else []
    )
    confidence_score = _compute_confidence(
        normalized_query,
        chunks,
        summary,
        missing_critical_details=clinical_features.missing_critical_details,
    )
    clarification_needed = (
        needs_clarification(
            confidence_score,
            triage_level,
            missing_critical_details=clinical_features.missing_critical_details,
        )
        or unsupported_reasoner_high
    )
    clarification_questions: list[ClarificationQuestion] = []
    if clarification_needed:
        reasoner_questions = _usable_reasoner_questions(
            getattr(summary, "clarification_questions", []),
            clinical_features,
        )
        clarification_questions = (
            localize_questions(reasoner_questions, response_language)
            if reasoner_questions
            else get_clarification_questions(
                normalized_query,
                summary=summary,
                recommended_specialty=recommended_specialty,
                triage_level=triage_level,
                clinical_features=clinical_features,
                language=response_language,
            )
        )
    supporting_reference_chunks = _filter_supporting_reference_chunks(reasoner_chunks)
    if not supporting_reference_chunks:
        supporting_reference_chunks = chunks
    if specialty_adjudication.relevant_reference_titles:
        selected_titles = {
            title.strip().lower()
            for title in specialty_adjudication.relevant_reference_titles
            if title.strip()
        }
        adjudicated_reference_chunks = [
            chunk
            for chunk in supporting_reference_chunks
            if getattr(chunk, "title", "").strip().lower() in selected_titles
        ]
        if adjudicated_reference_chunks:
            supporting_reference_chunks = adjudicated_reference_chunks
    condition_reference_chunks = _filter_reference_chunks_by_conditions(
        supporting_reference_chunks,
        display_conditions,
    )
    if condition_reference_chunks:
        supporting_reference_chunks = condition_reference_chunks
    elif display_conditions:
        supporting_reference_chunks = _filter_reference_chunks_by_features(
            supporting_reference_chunks,
            clinical_features,
        )

    logger.info(
        "triage_completed triage_level=%s query_length=%s contexts=%s "
        "specialty=%s condition=%s confidence=%s unsupported_reasoner_high=%s "
        "specialty_adjudication_confidence=%s",
        triage_level,
        len(normalized_query),
        len(contexts),
        recommended_specialty,
        suspected_condition,
        confidence_score,
        unsupported_reasoner_high,
        specialty_adjudication.confidence,
    )

    urgency_reason = (
        "The current description does not show a clear emergency warning sign, "
        "but more detail is needed before deciding how urgent this is."
        if unsupported_reasoner_high
        else (
            _preview_text(summary_text)
            if summary_text
            else (
                " ".join(summary.red_flags[:2])
                if hasattr(summary, "red_flags") and summary.red_flags
                else normalized_query
            )
        )
    )

    recommended_actions = (
        actions
        if unsupported_reasoner_high or triage_level == "high"
        else (
            summary.recommended_actions
            if hasattr(summary, "recommended_actions") and summary.recommended_actions
            else actions
        )
    )
    response_red_flags = (
        []
        if unsupported_reasoner_high
        else _patient_facing_red_flags(
            summary.red_flags if hasattr(summary, "red_flags") else [],
            triage_level,
        )
    )

    response = TriageResponse(
        triage_level=triage_level,
        urgency_level=triage_level,
        confidence_score=confidence_score,
        needs_clarification=clarification_needed,
        urgency_label=(
            "High"
            if triage_level == "high"
            else "Medium" if triage_level == "medium" else "Low"
        ),
        urgency_reason=urgency_reason,
        summary=summary_text,
        clinical_summary=summary_text,
        simple_reasoning=simple_reasoning,
        plain_language_explanation=(
            summary.patient_friendly_explanation
            if hasattr(summary, "patient_friendly_explanation")
            else simple_reasoning
        ),
        patient_friendly_explanation=(
            summary.patient_friendly_explanation
            if hasattr(summary, "patient_friendly_explanation")
            else simple_reasoning
        ),
        actions=recommended_actions,
        recommended_actions=recommended_actions,
        red_flags=response_red_flags,
        recommended_specialty=recommended_specialty,
        specialty_reason=specialty_reason,
        suspected_condition=suspected_condition,
        suspected_conditions=[
            {
                "name": getattr(c, "name", ""),
                "likelihood": getattr(c, "likelihood", "possible"),
                "explanation": getattr(c, "explanation", ""),
            }
            for c in display_conditions
        ],
        supporting_references=(
            [
                {
                    "title": c.title,
                    "source": c.source,
                    "url": c.url,
                    "snippet": c.text[:400] if c.text else "",
                }
                for c in supporting_reference_chunks[: settings.rag_top_k]
            ]
            if supporting_reference_chunks
            else []
        ),
        suggested_doctors=suggested_doctors,
        history_used=history_used,
        questions=clarification_questions,
        disclaimer=(
            "This is not medical advice. If you think you may have a medical "
            "emergency, seek immediate care."
        ),
    )
    return localize_triage_response(response, response_language)


def _compute_confidence(
    query: str,
    chunks: list,
    summary,
    *,
    missing_critical_details: list[str] | None = None,
) -> float:
    score = 1.0
    words = query.strip().split()

    # Short vague query
    if len(words) < 4:
        score -= 0.3
    elif len(words) < 6:
        score -= 0.1

    # Low RAG similarity
    if chunks:
        top_score = max((getattr(c, "score", 0) for c in chunks), default=0)
        if top_score < 0.45:
            score -= 0.25
        elif top_score < 0.55:
            score -= 0.1

    # Few conditions identified
    conditions = getattr(summary, "possible_conditions", [])
    if len(conditions) < 2:
        score -= 0.2

    # Catch-all specialty
    if getattr(summary, "recommended_specialty", "") == "Internal Medicine":
        score -= 0.1

    missing_count = len(missing_critical_details or [])
    if missing_count >= 3:
        score -= 0.2
    elif missing_count:
        score -= 0.1

    return round(max(0.0, min(1.0, score)), 2)
