from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DoctorProfile, User
from app.model.reasoner import OllamaReasoner, Reasoner, StubReasoner
from app.patient_symptoms import PATIENT_SYMPTOM_KEYWORDS
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.retriever import RetrievedChunk, Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.schemas.triage import (
    DoctorSuggestion,
    StructuredReasoningOutput,
    SupportingReference,
    SuspectedCondition,
    TriageLevel,
    TriageResponse,
)
from app.services.access_control import ensure_patient_profile_access
from app.services.patient_context import PatientContextProvider

logger = logging.getLogger(__name__)

LEVEL_PRIORITY: dict[TriageLevel, int] = {
    "low": 0,
    "medium": 1,
    "high": 2,
}

HIGH_RISK_KEYWORDS: tuple[str, ...] = (
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
    "blue lips",
)

MEDIUM_RISK_KEYWORDS: tuple[str, ...] = (
    "fever",
    "vomiting",
    "dehydration",
    "fracture",
    "burn",
    "infection",
    "migraine",
    "dizziness",
)

HEAD_TRAUMA_TERMS: tuple[str, ...] = (
    "hit my head",
    "hit my head hard",
    "head injury",
    "head trauma",
    "banged my head",
    "injured my head",
    "fell and hit my head",
    "after hitting my head",
    "concussion",
)
SEVERE_HEADACHE_TERMS: tuple[str, ...] = (
    "very painful headache",
    "severe headache",
    "worst headache",
    "worst of my life",
    "sudden bad headache",
    "bad headache",
    "head is killing me",
    "pounding headache",
    "throbbing headache",
)
NAUSEA_VOMITING_TERMS: tuple[str, ...] = (
    "nausea",
    "nauseous",
    "vomit",
    "vomiting",
    "throwing up",
    "gonna throw up",
)
ALTERED_MENTAL_STATUS_TERMS: tuple[str, ...] = (
    "confusion",
    "confused",
    "drowsy",
    "drowsiness",
    "hard to wake",
    "loss of consciousness",
    "passed out",
    "blackout",
    "black out",
    "fainting",
    "fainted",
)
BREATHING_DISTRESS_TERMS: tuple[str, ...] = (
    "shortness of breath",
    "difficulty breathing",
    "can't breathe",
    "cannot breathe",
    "trouble breathing",
    "blue lips",
    "wheezing badly",
)
STROKE_TERMS: tuple[str, ...] = (
    "slurred speech",
    "face drooping",
    "one-sided weakness",
    "one sided weakness",
    "can not move one side",
    "can't move one side",
    "sudden weakness",
    "sudden numbness",
    "sudden trouble speaking",
)
BLEEDING_TERMS: tuple[str, ...] = (
    "severe bleeding",
    "heavy bleeding",
    "won't stop bleeding",
    "bleeding a lot",
)
SEVERE_ALLERGY_TERMS: tuple[str, ...] = (
    "throat closing",
    "tongue swelling",
    "swelling face",
    "anaphylaxis",
    "can't swallow",
)
SEVERE_ABDOMINAL_TERMS: tuple[str, ...] = (
    "severe abdominal pain",
    "severe stomach pain",
    "worst stomach pain",
    "rigid abdomen",
    "abdomen is hard",
)
GI_MISLEADING_KEYWORDS_DURING_HEAD_TRAUMA: set[str] = {
    "feel nauseous",
    "feeling sick",
    "gonna throw up",
    "throwing up",
    "vomiting",
    "stomach upset",
    "upset stomach",
}

NEURO_EMERGENCY_EVIDENCE_TERMS: tuple[str, ...] = (
    "concussion",
    "intracranial hematoma",
    "subarachnoid hemorrhage",
    "brain aneurysm",
    "traumatic brain injury",
    "high intracranial pressure",
)
CARDIO_EMERGENCY_EVIDENCE_TERMS: tuple[str, ...] = (
    "myocardial infarction",
    "acute coronary syndrome",
    "pulmonary embolism",
    "heart attack",
)
RESPIRATORY_EMERGENCY_EVIDENCE_TERMS: tuple[str, ...] = (
    "pneumonia",
    "asthma",
    "anaphylaxis",
    "airway",
)

SPECIALTY_RULES: dict[str, tuple[str, ...]] = {
    "Cardiology": (
        "heart",
        "cardiac",
        "coronary",
        "myocardial",
        "palpitations",
        "arrhythmia",
        "hypertension",
        "chest pain",
    ),
    "Pulmonology": (
        "asthma",
        "copd",
        "bronchitis",
        "pneumonia",
        "lung",
        "breath",
        "breathing",
        "cough",
        "respiratory",
        "allergy",
    ),
    "Gastroenterology": (
        "stomach",
        "gastritis",
        "gerd",
        "appendicitis",
        "bowel",
        "diarrhea",
        "abdominal",
        "hepatology",
        "gastroenterology",
    ),
    "Neurology": (
        "migraine",
        "stroke",
        "meningitis",
        "vertigo",
        "neuropathy",
        "seizure",
        "headache",
        "concussion",
        "intracranial",
        "brain injury",
        "brain aneurysm",
        "hematoma",
        "head trauma",
    ),
    "Orthopedics": (
        "fracture",
        "sprain",
        "strain",
        "arthritis",
        "joint",
        "back pain",
        "knee",
        "bone",
        "trauma",
    ),
    "Dermatology": (
        "rash",
        "eczema",
        "psoriasis",
        "skin",
        "itching",
        "acne",
    ),
    "Psychiatry": (
        "panic",
        "anxiety",
        "depression",
        "suicidal",
        "mental",
        "overwhelmed",
    ),
    "Internal Medicine": (
        "fever",
        "infection",
        "flu",
        "viral",
        "fatigue",
        "weight loss",
        "dizziness",
    ),
}

SPECIALTY_FALLBACKS: dict[str, tuple[str, ...]] = {
    "Neurology": ("Neurology", "Internal Medicine"),
    "Pulmonology": ("Pulmonology", "Internal Medicine"),
    "Cardiology": ("Cardiology", "Internal Medicine"),
    "Gastroenterology": ("Gastroenterology", "Internal Medicine"),
    "Orthopedics": ("Orthopedics",),
    "Psychiatry": ("Psychiatry",),
    "Dermatology": ("Dermatology",),
    "Internal Medicine": ("Internal Medicine",),
}


@dataclass
class RankedCondition:
    name: str
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RedFlagAssessment:
    urgency_floor: TriageLevel
    warning_labels: tuple[str, ...] = ()
    priority_conditions: tuple[str, ...] = ()
    specialty_override: str | None = None
    patient_message: str | None = None
    clinical_note: str | None = None
    recommended_actions: tuple[str, ...] = ()
    evidence_keywords: tuple[str, ...] = ()


def _match_any(query: str, keywords: tuple[str, ...]) -> list[str]:
    lowered = query.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def _chunk_contains_terms(chunk: RetrievedChunk, terms: tuple[str, ...]) -> bool:
    searchable = f"{chunk.title} {chunk.text}".lower()
    return any(term in searchable for term in terms)


def _heuristic_urgency(query: str) -> tuple[TriageLevel, list[str]]:
    red_flags = _match_any(query, HIGH_RISK_KEYWORDS)
    if red_flags:
        return "high", red_flags

    caution_flags = _match_any(query, MEDIUM_RISK_KEYWORDS)
    if caution_flags:
        return "medium", caution_flags

    return "low", []


def _assess_red_flags(
    query: str,
    patient_context: str | None,
    chunks: list[RetrievedChunk],
) -> RedFlagAssessment:
    combined_text = f"{query}\n{patient_context or ''}".lower()
    warnings: list[str] = []
    conditions: list[str] = []
    actions: list[str] = []
    evidence_keywords: list[str] = []
    patient_message: str | None = None
    clinical_note: str | None = None
    specialty_override: str | None = None
    urgency_floor: TriageLevel = "low"

    head_trauma = any(term in combined_text for term in HEAD_TRAUMA_TERMS)
    severe_headache = any(term in combined_text for term in SEVERE_HEADACHE_TERMS)
    nausea_or_vomiting = any(term in combined_text for term in NAUSEA_VOMITING_TERMS)
    altered_mental_status = any(
        term in combined_text for term in ALTERED_MENTAL_STATUS_TERMS
    )
    chest_pain = "chest pain" in combined_text or "chest tightness" in combined_text
    breathing_distress = any(
        term in combined_text for term in BREATHING_DISTRESS_TERMS
    )
    stroke_symptoms = any(term in combined_text for term in STROKE_TERMS)
    severe_bleeding = any(term in combined_text for term in BLEEDING_TERMS)
    seizure_like = "seizure" in combined_text or "convulsion" in combined_text
    suicidal = "suicidal" in combined_text or "hurt myself" in combined_text
    severe_allergy = any(term in combined_text for term in SEVERE_ALLERGY_TERMS)
    severe_abdominal = any(term in combined_text for term in SEVERE_ABDOMINAL_TERMS)

    if head_trauma and (severe_headache or nausea_or_vomiting or altered_mental_status):
        urgency_floor = "high"
        specialty_override = "Neurology"
        warnings.append("Recent head injury with severe headache, vomiting, or drowsiness")
        conditions.extend(
            [
                "Intracranial hematoma",
                "Concussion",
                "Traumatic brain injury",
            ]
        )
        evidence_keywords.extend(NEURO_EMERGENCY_EVIDENCE_TERMS)
        actions.extend(
            [
                "Go to the emergency department now for urgent brain injury assessment.",
                "Do not drive yourself if you feel drowsy, confused, or are vomiting.",
            ]
        )
        patient_message = (
            "Because you recently injured your head and now have severe headache "
            "with nausea or vomiting, this could be a serious head injury rather "
            "than a stomach problem. You should get urgent medical assessment now."
        )
        clinical_note = (
            "Recent head trauma followed by severe headache and nausea or vomiting "
            "raises concern for concussion or intracranial bleeding."
        )

    if chest_pain and breathing_distress:
        urgency_floor = "high"
        specialty_override = specialty_override or "Cardiology"
        warnings.append("Chest pain with shortness of breath")
        conditions.extend(["Acute coronary syndrome", "Pulmonary embolism"])
        evidence_keywords.extend(CARDIO_EMERGENCY_EVIDENCE_TERMS)
        actions.extend(
            [
                "Seek urgent or emergency care now for chest pain with breathing trouble.",
                "Call emergency services if the pain is severe, crushing, or worsening.",
            ]
        )
        patient_message = patient_message or (
            "Chest pain together with shortness of breath can signal a serious heart "
            "or lung emergency. Please seek urgent medical care now."
        )
        clinical_note = clinical_note or (
            "Chest pain with dyspnea requires urgent exclusion of cardiac or pulmonary emergencies."
        )

    if stroke_symptoms:
        urgency_floor = "high"
        specialty_override = specialty_override or "Neurology"
        warnings.append("Stroke-like symptoms")
        conditions.extend(["Acute ischemic stroke", "Transient ischemic attack"])
        actions.extend(
            [
                "Seek emergency care immediately for possible stroke symptoms.",
                "Do not wait to see if weakness or speech problems improve on their own.",
            ]
        )
        patient_message = patient_message or (
            "Sudden weakness, numbness, facial drooping, or speech trouble can point "
            "to a stroke and need emergency medical attention now."
        )
        clinical_note = clinical_note or (
            "Stroke-like symptoms require immediate neurological assessment."
        )

    if breathing_distress and not chest_pain:
        urgency_floor = "high"
        specialty_override = specialty_override or "Pulmonology"
        warnings.append("Severe breathing difficulty")
        conditions.extend(["Asthma exacerbation", "Severe respiratory distress"])
        evidence_keywords.extend(RESPIRATORY_EMERGENCY_EVIDENCE_TERMS)
        actions.extend(
            [
                "Seek urgent care immediately if breathing is difficult or getting worse.",
                "Call emergency services if lips turn blue or speaking becomes hard.",
            ]
        )

    if severe_bleeding:
        urgency_floor = "high"
        warnings.append("Heavy bleeding")
        actions.extend(
            [
                "Apply pressure if possible and seek emergency care immediately.",
                "Call emergency services if bleeding is heavy or will not stop.",
            ]
        )
        patient_message = patient_message or (
            "Heavy bleeding is an emergency and should be treated immediately."
        )
        clinical_note = clinical_note or "Uncontrolled bleeding requires emergency assessment."

    if seizure_like:
        urgency_floor = "high"
        specialty_override = specialty_override or "Neurology"
        warnings.append("Seizure or convulsion")
        conditions.append("Seizure disorder")
        actions.extend(
            [
                "Seek emergency care if a seizure has occurred or if recovery is incomplete.",
                "Urgent review is needed, especially if this is the first seizure.",
            ]
        )

    if suicidal:
        urgency_floor = "high"
        specialty_override = specialty_override or "Psychiatry"
        warnings.append("Thoughts of self-harm")
        actions.extend(
            [
                "Seek emergency psychiatric help now or contact a crisis line immediately.",
                "Stay with a trusted person and avoid being alone until help is in place.",
            ]
        )
        patient_message = patient_message or (
            "Thoughts of self-harm need urgent support right away. Please contact emergency "
            "or crisis services now."
        )

    if severe_allergy:
        urgency_floor = "high"
        specialty_override = specialty_override or "Pulmonology"
        warnings.append("Possible severe allergic reaction")
        conditions.append("Anaphylaxis")
        actions.extend(
            [
                "Use emergency allergy treatment if prescribed and seek emergency care now.",
                "Call emergency services if throat swelling or breathing difficulty is present.",
            ]
        )

    if severe_abdominal and nausea_or_vomiting:
        urgency_floor = max(
            urgency_floor,
            "medium",
            key=lambda level: LEVEL_PRIORITY[level],
        )
        specialty_override = specialty_override or "Gastroenterology"
        warnings.append("Severe abdominal pain with vomiting")
        conditions.extend(["Appendicitis", "Bowel obstruction", "Peritonitis"])
        actions.extend(
            [
                "Seek urgent same-day assessment for severe abdominal pain with vomiting.",
                "Go sooner if fever, fainting, or worsening pain develops.",
            ]
        )
        patient_message = patient_message or (
            "Severe abdominal pain together with vomiting needs prompt medical review today."
        )

    if any(
        _chunk_contains_terms(chunk, NEURO_EMERGENCY_EVIDENCE_TERMS)
        for chunk in chunks[:3]
    ) and head_trauma:
        urgency_floor = "high"
        if specialty_override is None:
            specialty_override = "Neurology"
        if (
            "Dangerous head-injury references matched the symptom description"
            not in warnings
        ):
            warnings.append(
                "Dangerous head-injury references matched the symptom description"
            )

    if not warnings:
        return RedFlagAssessment(urgency_floor=urgency_floor)

    return RedFlagAssessment(
        urgency_floor=urgency_floor,
        warning_labels=tuple(dict.fromkeys(warnings)),
        priority_conditions=tuple(dict.fromkeys(conditions)),
        specialty_override=specialty_override,
        patient_message=patient_message,
        clinical_note=clinical_note,
        recommended_actions=tuple(dict.fromkeys(actions)),
        evidence_keywords=tuple(dict.fromkeys(evidence_keywords)),
    )


def _build_actions(
    triage_level: TriageLevel,
    specialty: str,
    reasoner_actions: list[str],
    red_flag_actions: tuple[str, ...] = (),
) -> list[str]:
    if triage_level == "high":
        actions = [
            "Seek urgent or emergency medical care now.",
            "Call local emergency services if symptoms are severe or worsening.",
        ]
    elif triage_level == "medium":
        actions = [
            "Arrange medical review soon, ideally today or within 24 hours.",
            "Seek faster care if symptoms worsen or new warning signs appear.",
        ]
    else:
        actions = [
            "Monitor your symptoms, rest, and stay hydrated if appropriate.",
            "Book a medical review if symptoms persist, worsen, or worry you.",
        ]

    if specialty and specialty != "General Practice":
        actions.append(f"Consider booking a {specialty} appointment.")

    for action in [*red_flag_actions, *reasoner_actions]:
        cleaned = action.strip()
        if cleaned and cleaned not in actions:
            actions.append(cleaned)

    return actions[:5]


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

        if settings.strict_reasoner:
            raise RuntimeError(
                f"Ollama reasoner is required but unreachable at {settings.ollama_host}"
            )

        logger.warning("reasoner_fallback_to_stub reason=ollama_unreachable")
        return StubReasoner()

    logger.warning("reasoner_mode_unknown value=%s fallback=stub", mode)
    logger.info("reasoner_initialized mode=stub model=none")
    return StubReasoner()


@lru_cache
def get_reasoner() -> Reasoner:
    return _build_reasoner()


def clear_runtime_state() -> None:
    get_retriever.cache_clear()
    get_reasoner.cache_clear()


def simplify_reasoning(text: str) -> str:
    replacements = {
        "cardiac": "heart",
        "cardiovascular": "heart and blood vessel",
        "respiratory": "breathing",
        "pulmonary": "lung",
        "gastrointestinal": "digestive",
        "neurological": "brain and nerve",
        "dermatological": "skin",
        "musculoskeletal": "bone and muscle",
        "infectious": "infection-related",
        "diagnosis": "possible condition",
        "acute": "sudden",
        "chronic": "long-term",
        "exacerbation": "flare-up",
        "contraindication": "risk",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
        result = result.replace(source.capitalize(), target.capitalize())
    return result


def _format_chunk_for_reasoner(chunk: RetrievedChunk) -> str:
    header = f"{chunk.title} ({chunk.source})"
    if chunk.url:
        header = f"{header} - {chunk.url}"
    snippet = chunk.text.strip()
    if len(snippet) > 420:
        snippet = f"{snippet[:420].rstrip()}..."
    return f"{header}\n{snippet}"


def _build_supporting_references(
    chunks: list[RetrievedChunk],
) -> list[SupportingReference]:
    references: list[SupportingReference] = []
    seen: set[tuple[str, str]] = set()
    for chunk in chunks[:4]:
        key = (chunk.title.lower(), chunk.url)
        if key in seen:
            continue
        seen.add(key)
        snippet = chunk.text.strip()
        if len(snippet) > 220:
            snippet = f"{snippet[:220].rstrip()}..."
        references.append(
            SupportingReference(
                title=chunk.title,
                source=chunk.source,
                url=chunk.url or None,
                snippet=snippet,
            )
        )
    return references


def _normalize_condition_name(raw_name: str) -> str:
    return " ".join(raw_name.split()).strip(" .,-")


def _split_condition_names(raw_name: str) -> list[str]:
    return [
        _normalize_condition_name(part)
        for part in raw_name.replace(" or ", "/").split("/")
        if _normalize_condition_name(part)
    ]


def _add_condition_score(
    scores: dict[str, RankedCondition],
    condition_name: str,
    score: float,
    reason: str,
) -> None:
    normalized = _normalize_condition_name(condition_name)
    if not normalized or normalized.lower() == "unknown condition":
        return

    key = normalized.lower()
    entry = scores.get(key)
    if entry is None:
        entry = RankedCondition(name=normalized)
        scores[key] = entry

    entry.score += score
    if reason not in entry.reasons:
        entry.reasons.append(reason)


def _context_penalty(
    condition_name: str,
    red_flag_assessment: RedFlagAssessment,
) -> float:
    """Apply context-aware penalties to condition scores.
    
    Strongly penalizes conditions that don't match the clinical context
    raised by red flags. This prevents shallow keyword matching from
    incorrectly dominating the final ranking.
    """
    lowered = condition_name.lower()
    penalty = 0.0
    
    # Neurology red flags: penalize GI and non-neurological conditions
    if red_flag_assessment.specialty_override == "Neurology":
        if any(
            token in lowered
            for token in (
                "gerd",
                "gastritis",
                "gastroenteritis",
                "ibs",
                "reflux",
                "peptic ulcer",
                "appendicitis",
                "cholecystitis",
                "pancreatitis",
                "hepatitis",
            )
        ):
            penalty = -4.2  # Strongly demote GI in head trauma context
        elif any(
            token in lowered
            for token in (
                "anxiety",
                "panic",
                "depression",
            )
        ):
            penalty = -2.8  # Demote psychiatric conditions
    
    # Cardiology red flags: penalize GI and psychiatric conditions
    if red_flag_assessment.specialty_override == "Cardiology":
        if any(
            token in lowered
            for token in (
                "gerd",
                "gastritis",
                "anxiety",
                "panic disorder",
            )
        ):
            penalty = -2.4
    
    # Pulmonology red flags: penalize cardiac and GI conditions  
    if red_flag_assessment.specialty_override == "Pulmonology":
        if any(
            token in lowered
            for token in (
                "gerd",
                "myocardial infarction",
                "heart attack",
            )
        ):
            penalty = -2.0
    
    return penalty


def _collect_condition_scores(
    query: str,
    patient_context: str | None,
    chunks: list[RetrievedChunk],
    reasoning: StructuredReasoningOutput,
    red_flag_assessment: RedFlagAssessment,
) -> dict[str, RankedCondition]:
    """Collect and score suspected conditions.
    
    Scoring combines:
    1. Red flag priority conditions (highest weight)
    2. Retrieved medical evidence (weighted by rank and relevance)
    3. Symptom keyword matching (with context penalties)
    4. LLM reasoning suggestions
    5. Context-aware penalties for mismatched conditions
    """
    combined_text = query.lower()
    if patient_context:
        combined_text = f"{combined_text}\n{patient_context.lower()}"

    scores: dict[str, RankedCondition] = {}

    # Priority 1: Red flag conditions are critical to surface
    # These are conditions identified as dangerous in the symptom pattern
    for condition_name in red_flag_assessment.priority_conditions:
        _add_condition_score(
            scores,
            condition_name,
            6.8,  # Increased from 5.2 - red flags are non-negotiable
            "Red-flag symptom combination makes this condition important to exclude.",
        )

    # Priority 2: Retrieved evidence - medical literature matches this presentation
    # Weight by retrieval rank and relevance
    for index, chunk in enumerate(chunks[:6]):
        # Base weight decreases slightly with rank, but evidence is still valuable
        base_weight = max(1.0, 4.2 - (index * 0.35)) + max(chunk.score, 0.0)
        
        # Boost if evidence explicitly mentions red flag keywords
        if red_flag_assessment.evidence_keywords and _chunk_contains_terms(
            chunk,
            red_flag_assessment.evidence_keywords,
        ):
            base_weight += 3.2  # Increased from 2.5
        
        _add_condition_score(
            scores,
            chunk.title,
            base_weight,
            "Retrieved medical evidence matched this presentation.",
        )

    # Priority 3: Symptom keyword matching
    # But skip GI keywords during head trauma to avoid misleading matches
    for keyword, condition_text in PATIENT_SYMPTOM_KEYWORDS:
        if keyword not in combined_text:
            continue
        
        # Skip misleading keyword matches in high-context scenarios
        if (
            red_flag_assessment.specialty_override == "Neurology"
            and keyword in GI_MISLEADING_KEYWORDS_DURING_HEAD_TRAUMA
        ):
            continue
        
        for condition_name in _split_condition_names(condition_text):
            _add_condition_score(
                scores,
                condition_name,
                2.3,  # Slightly increased from 2.2
                f"Matches the symptom pattern '{keyword}'.",
            )

    # Priority 4: LLM reasoning suggestions
    # Weight by reasoning confidence (earlier suggestions weighted higher)
    for index, condition in enumerate(reasoning.possible_conditions[:3]):
        weight = 4.0 - (index * 1.0)  # Increased base from 3.7
        _add_condition_score(
            scores,
            condition.name,
            weight,
            condition.explanation,
        )

    # Priority 5: Apply context-aware penalties
    # Demote conditions that don't fit the clinical red flag context
    for condition in list(scores.values()):
        penalty = _context_penalty(condition.name, red_flag_assessment)
        if penalty:
            condition.score += penalty
            if penalty < 0:
                reason = (
                    "This became less likely after applying the higher-risk symptom context."
                )
                if reason not in condition.reasons:
                    condition.reasons.append(reason)

    return scores


def _build_suspected_conditions(
    condition_scores: dict[str, RankedCondition],
) -> list[SuspectedCondition]:
    ordered = sorted(
        condition_scores.values(),
        key=lambda item: item.score,
        reverse=True,
    )[:3]

    suspected: list[SuspectedCondition] = []
    for index, condition in enumerate(ordered):
        likelihood = (
            "more_likely" if index == 0 else "possible" if index == 1 else "less_likely"
        )
        suspected.append(
            SuspectedCondition(
                name=condition.name,
                likelihood=likelihood,
                explanation=(
                    condition.reasons[0]
                    if condition.reasons
                    else "This may fit the pattern of symptoms described."
                ),
            )
        )
    return suspected


def _determine_specialty(
    query: str,
    suspected_conditions: list[SuspectedCondition],
    reasoning: StructuredReasoningOutput,
    red_flag_assessment: RedFlagAssessment,
    chunks: list[RetrievedChunk],
) -> tuple[str, str | None]:
    """Determine recommended specialty based on clinical context.
    
    Priority order:
    1. Red flag assessment specialty override (highest priority - safety-critical)
    2. Suspected condition specialty rules
    3. Retrieved evidence specialty hints
    4. LLM reasoning specialty
    5. Default to General Practice
    """
    # Red flag overrides are safety-critical and must not be overridden
    if red_flag_assessment.specialty_override:
        reason = red_flag_assessment.clinical_note or (
            "The symptom combination contains warning signs that are safest under "
            f"{red_flag_assessment.specialty_override.lower()} review."
        )
        return red_flag_assessment.specialty_override, reason

    specialty_scores: defaultdict[str, float] = defaultdict(float)
    combined_text = " ".join(
        [query, *[condition.name for condition in suspected_conditions]]
    ).lower()

    # Score based on suspected conditions keywords
    for specialty, keywords in SPECIALTY_RULES.items():
        specialty_scores[specialty] += sum(
            1.0 for keyword in keywords if keyword in combined_text
        )

    # Score based on retrieved evidence
    for chunk in chunks[:4]:
        searchable = f"{chunk.title} {chunk.text}".lower()
        for specialty, keywords in SPECIALTY_RULES.items():
            specialty_scores[specialty] += sum(
                0.4 for keyword in keywords if keyword in searchable
            )

    # Incorporate LLM reasoning specialty suggestion
    if reasoning.recommended_specialty and reasoning.recommended_specialty.strip():
        specialty_scores[reasoning.recommended_specialty.strip()] += 1.5  # Increased from 1.2

    # If no meaningful scores, fall back to LLM or general practice
    if not specialty_scores or max(specialty_scores.values()) < 0.1:
        if reasoning.recommended_specialty and reasoning.recommended_specialty.strip():
            return reasoning.recommended_specialty.strip(), None
        return "General Practice", None

    best_specialty = max(specialty_scores.items(), key=lambda item: item[1])[0]
    reason = None
    if suspected_conditions:
        reason = (
            f"The leading possibilities and retrieved references fit best with "
            f"{best_specialty.lower()} care."
        )
    return best_specialty, reason


def get_suggested_doctors(
    db: Session | None,
    specialty: str,
    limit: int = 3,
) -> list[DoctorSuggestion]:
    if db is None or not specialty:
        return []

    search_terms = SPECIALTY_FALLBACKS.get(
        specialty,
        (specialty, specialty.split()[0]),
    )
    doctors: list[DoctorProfile] = []
    seen_ids: set[int] = set()

    for term in search_terms:
        matches = (
            db.query(DoctorProfile)
            .filter(
                or_(
                    DoctorProfile.specialty.ilike(f"%{term}%"),
                    DoctorProfile.clinic.ilike(f"%{term}%"),
                )
            )
            .order_by(DoctorProfile.full_name.asc())
            .limit(limit)
            .all()
        )
        for doctor in matches:
            if doctor.id in seen_ids:
                continue
            doctors.append(doctor)
            seen_ids.add(doctor.id)
            if len(doctors) >= limit:
                break
        if len(doctors) >= limit:
            break

    return [
        DoctorSuggestion(
            id=doctor.id,
            full_name=doctor.full_name,
            specialty=doctor.specialty,
            clinic=doctor.clinic,
            area=doctor.area,
            city=doctor.city,
            source_name=doctor.source_name,
            source_url=doctor.source_url,
            booking_url=doctor.booking_url,
        )
        for doctor in doctors
    ]


def _combine_urgency(
    heuristic_level: TriageLevel,
    model_level: TriageLevel,
    red_flags: list[str],
    red_flag_assessment: RedFlagAssessment,
    chunks: list[RetrievedChunk],
) -> TriageLevel:
    """Determine final urgency level, prioritizing safety.
    
    The final urgency must reflect:
    1. Red flag urgency floor (highest priority)
    2. Retrieved evidence supporting dangerous conditions
    3. Heuristic and LLM reasoning
    
    Safety rules ensure serious cases aren't downgraded.
    """
    # Start with the red flag urgency floor as the baseline
    final_level: TriageLevel = red_flag_assessment.urgency_floor
    
    # Never downgrade from high urgency due to conflicting signals
    if red_flag_assessment.urgency_floor == "high":
        return "high"
    
    # Incorporate heuristic and model signals
    signals = [heuristic_level, model_level]
    for signal in signals:
        if LEVEL_PRIORITY[signal] > LEVEL_PRIORITY[final_level]:
            final_level = signal
    
    # If dangerous evidence keywords were found, ensure at least MEDIUM
    if red_flag_assessment.evidence_keywords and any(
        _chunk_contains_terms(chunk, red_flag_assessment.evidence_keywords)
        for chunk in chunks[:3]
    ):
        if LEVEL_PRIORITY.get("medium", 0) > LEVEL_PRIORITY.get(final_level, -1):
            final_level = "medium"
    
    # Red flags present but not yet elevated? Bump to medium
    if red_flags and final_level == "low":
        final_level = "medium"
    
    return final_level


def _urgency_label(level: TriageLevel, red_flag_assessment: RedFlagAssessment) -> str:
    if level == "high":
        if red_flag_assessment.urgency_floor == "high":
            return "Emergency assessment needed now"
        return "Urgent or emergency assessment advised"
    if level == "medium":
        return "Prompt medical review advised"
    return "Monitor and arrange routine review if needed"


def _merge_red_flags(
    heuristic_flags: list[str],
    reasoning_flags: list[str],
    red_flag_assessment: RedFlagAssessment,
) -> list[str]:
    merged: list[str] = []
    for flag in [
        *red_flag_assessment.warning_labels,
        *heuristic_flags,
        *reasoning_flags,
    ]:
        cleaned = flag.strip()
        if cleaned and cleaned not in merged:
            merged.append(cleaned)
    return merged[:5]


def _build_disclaimer(level: TriageLevel) -> str:
    if level == "high":
        return (
            "This is not a diagnosis. Because your symptoms may be urgent, seek "
            "emergency care now or contact local emergency services."
        )
    return (
        "This triage result lists possible conditions, not a confirmed diagnosis. "
        "Please contact a licensed clinician for medical advice, especially if "
        "symptoms worsen or new warning signs appear."
    )


def _compose_explanations(
    reasoning: StructuredReasoningOutput,
    red_flag_assessment: RedFlagAssessment,
    suspected_conditions: list[SuspectedCondition],
) -> tuple[str, str, str | None]:
    clinical_summary = reasoning.clinical_summary.strip()
    patient_explanation = reasoning.patient_friendly_explanation.strip()
    urgency_reason = None

    if red_flag_assessment.clinical_note:
        urgency_reason = red_flag_assessment.clinical_note
        if red_flag_assessment.patient_message:
            patient_explanation = red_flag_assessment.patient_message
        if (
            not clinical_summary
            or clinical_summary == reasoning.patient_friendly_explanation.strip()
        ):
            clinical_summary = red_flag_assessment.clinical_note

    if not patient_explanation and suspected_conditions:
        patient_explanation = (
            f"Your symptoms may be related to {suspected_conditions[0].name}. "
            "Please use the urgency level and next steps below to decide how quickly "
            "to get help."
        )

    return clinical_summary, patient_explanation, urgency_reason


def triage(
    query: str,
    patient_id: int | None = None,
    db: Session | None = None,
    current_user: User | None = None,
) -> TriageResponse:
    normalized_query = query.strip()
    settings = get_settings()
    heuristic_level, heuristic_flags = _heuristic_urgency(normalized_query)

    retrieved_chunks = get_retriever().retrieve_chunks(
        normalized_query,
        top_k=settings.rag_top_k,
    )
    contexts = [_format_chunk_for_reasoner(chunk) for chunk in retrieved_chunks]

    patient_context: str | None = None
    history_used = False
    if patient_id is not None:
        if db is None:
            raise RuntimeError("Database session is required for patient-aware triage.")
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Authentication is required to run triage with linked patient "
                    "history."
                ),
            )

        ensure_patient_profile_access(db, current_user, patient_id)
        provider = PatientContextProvider(
            visit_limit=settings.patient_history_visit_limit,
            top_matches=settings.patient_history_top_matches,
        )
        patient_result = provider.build(db, patient_id, normalized_query)
        patient_context = patient_result.context_text
        history_used = patient_result.history_used
        logger.info(
            "triage_history_context_loaded patient_id=%s matches=%s",
            patient_id,
            len(patient_result.matched_visit_ids),
        )

    red_flag_assessment = _assess_red_flags(
        normalized_query,
        patient_context,
        retrieved_chunks,
    )

    baseline_level = max(
        heuristic_level,
        red_flag_assessment.urgency_floor,
        key=lambda level: LEVEL_PRIORITY[level],
    )
    reasoning = get_reasoner().reason(
        normalized_query,
        contexts,
        baseline_level,
        patient_context=patient_context,
    )
    merged_red_flags = _merge_red_flags(
        heuristic_flags,
        reasoning.red_flags,
        red_flag_assessment,
    )
    urgency_level = _combine_urgency(
        heuristic_level,
        reasoning.urgency_level,
        merged_red_flags,
        red_flag_assessment,
        retrieved_chunks,
    )

    condition_scores = _collect_condition_scores(
        normalized_query,
        patient_context,
        retrieved_chunks,
        reasoning,
        red_flag_assessment,
    )
    suspected_conditions = _build_suspected_conditions(condition_scores)
    recommended_specialty, specialty_reason = _determine_specialty(
        normalized_query,
        suspected_conditions,
        reasoning,
        red_flag_assessment,
        retrieved_chunks,
    )
    suggested_doctors = get_suggested_doctors(db, recommended_specialty)
    recommended_actions = _build_actions(
        urgency_level,
        recommended_specialty,
        reasoning.recommended_actions,
        red_flag_actions=red_flag_assessment.recommended_actions,
    )
    supporting_references = _build_supporting_references(retrieved_chunks)

    clinical_summary, patient_explanation, urgency_reason = _compose_explanations(
        reasoning,
        red_flag_assessment,
        suspected_conditions,
    )
    simple_reasoning = simplify_reasoning(clinical_summary)
    top_condition = suspected_conditions[0].name if suspected_conditions else None

    logger.info(
        "triage_completed urgency=%s query_length=%s evidence=%s specialty=%s",
        urgency_level,
        len(normalized_query),
        len(retrieved_chunks),
        recommended_specialty,
    )

    return TriageResponse(
        triage_level=urgency_level,
        urgency_level=urgency_level,
        urgency_label=_urgency_label(urgency_level, red_flag_assessment),
        urgency_reason=urgency_reason,
        summary=patient_explanation,
        clinical_summary=clinical_summary,
        simple_reasoning=simple_reasoning,
        plain_language_explanation=patient_explanation,
        patient_friendly_explanation=patient_explanation,
        actions=recommended_actions,
        recommended_actions=recommended_actions,
        red_flags=merged_red_flags,
        recommended_specialty=recommended_specialty,
        specialty_reason=specialty_reason,
        suspected_condition=top_condition,
        suspected_conditions=suspected_conditions,
        suggested_doctors=suggested_doctors,
        supporting_references=supporting_references,
        history_used=history_used,
        disclaimer=_build_disclaimer(urgency_level),
    )
