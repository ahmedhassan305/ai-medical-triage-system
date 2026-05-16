from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import DoctorProfile
from app.model.reasoner import OllamaReasoner, Reasoner, StubReasoner
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.reranker import rerank_retrieved_chunks
from app.rag.retriever import Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.schemas.triage import DoctorSuggestion, TriageLevel, TriageResponse
from app.services.clarification_service import (
    get_clarification_questions,
    needs_clarification,
)
from app.services.patient_context import PatientContextProvider
from app.patient_symptoms import PATIENT_SYMPTOM_KEYWORDS

logger = logging.getLogger(__name__)

TRIAGE_LEVEL_RANK: dict[TriageLevel, int] = {"low": 0, "medium": 1, "high": 2}
MIN_REASONER_RAG_SCORE = 0.48
MIN_SUPPORTING_REFERENCE_SCORE = 0.5
RAG_CANDIDATE_MULTIPLIER = 6
REASONER_RAG_LIMIT = 5
VALID_SPECIALTIES = (
    "Cardiology",
    "Neurology",
    "Neurosurgery",
    "Internal Medicine",
    "Gastroenterology",
    "Dermatology",
    "Psychiatry",
    "Ophthalmology",
    "Orthopedics",
    "ENT",
    "Pediatrics",
    "Family Medicine",
)
SPECIALTY_ALIASES = {
    "pulmonology": "Internal Medicine",
    "pulmonary": "Internal Medicine",
    "respiratory": "Internal Medicine",
    "general practice": "Family Medicine",
    "primary care": "Family Medicine",
    "otolaryngology": "ENT",
    "ear nose throat": "ENT",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "cardiac": "Cardiology",
}

HIGH_RISK_KEYWORDS: tuple[str, ...] = (
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "can't breathe",
    "cannot breathe",
    "suffocating",
    "suffocation",
    "choking",
    "pass out",
    "passing out",
    "blacked out",
    "fainted",
    "fainting",
    "stroke",
    "seizure",
    "unconscious",
    "unresponsive",
    "severe bleeding",
    "overdose",
    "suicidal",
    "heart attack",
    "not breathing",
)

MEDIUM_RISK_KEYWORDS: tuple[str, ...] = (
    "fever",
    "vomiting",
    "dehydration",
    "fracture",
    "burn",
    "infection",
    "migraine",
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


def _format_reasoner_context(chunk) -> str:
    header = f"({chunk.source}) {chunk.title}"
    if chunk.url:
        header = f"{header} - {chunk.url}"
    return f"{header}\n[score: {chunk.score:.4f}]\n{chunk.text}"


def _normalize_recommended_specialty(
    specialty: str | None,
    query: str,
    triage_level: TriageLevel,
) -> str:
    if specialty:
        import re as _re

        candidate = _re.split(r" or |and/or|/|,|;", specialty, maxsplit=1)[0].strip()
        candidate = candidate.split("(")[0].strip()
        if candidate in VALID_SPECIALTIES:
            return "Internal Medicine" if candidate == "Family Medicine" else candidate

        lower_candidate = candidate.lower()
        for alias, normalized in SPECIALTY_ALIASES.items():
            if alias in lower_candidate:
                return "Internal Medicine" if normalized == "Family Medicine" else normalized

    lowered_query = query.lower()
    if triage_level == "high" and (
        "chest pain" in lowered_query
        or "heart attack" in lowered_query
        or "shortness of breath" in lowered_query
    ):
        return "Cardiology"
    if any(term in lowered_query for term in ("baby", "child", "toddler", "infant")):
        return "Pediatrics"
    return "Internal Medicine"


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




def _preload_model() -> None:
    """Preload the LLM model into VRAM on startup."""
    import httpx as _httpx
    import os as _os
    host = _os.getenv('OLLAMA_HOST', 'http://localhost:11434').rstrip('/')
    model = _os.getenv('OLLAMA_MODEL', 'llama3.2:3b')
    try:
        logger.info('preloading_model model=%s', model)
        with _httpx.Client(timeout=60.0) as client:
            client.post(f'{host}/api/generate', json={
                'model': model,
                'prompt': 'hi',
                'stream': False,
                'options': {'num_predict': 1},
            })
        logger.info('model_preloaded model=%s', model)
    except Exception as e:
        logger.warning('model_preload_failed error=%s', e)

def clear_runtime_state() -> None:
    get_retriever.cache_clear()
    get_reasoner.cache_clear()


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


def get_recommended_specialty(query: str, summary: str) -> str:
    """Extract recommended medical specialty from query and summary."""
    specialty_keywords = {
        # Emergency
        "suffocating": "Emergency Medicine",
        "pass out": "Emergency Medicine",
        "passing out": "Emergency Medicine",
        "fainting": "Emergency Medicine",
        "can't breathe": "Emergency Medicine",
        "cannot breathe": "Emergency Medicine",
        "heart attack": "Emergency Medicine",
        # Cardiology
        "cardio": "Cardiology",
        "heart": "Cardiology",
        "chest pain": "Cardiology",
        "blood pressure": "Cardiology",
        "arrhythmia": "Cardiology",
        "palpitations": "Cardiology",
        # Pulmonology
        "respir": "Pulmonology",
        "lung": "Pulmonology",
        "breathing": "Pulmonology",
        "asthma": "Pulmonology",
        "cough": "Pulmonology",
        "pneumonia": "Pulmonology",
        "bronch": "Pulmonology",
        # Gastroenterology
        "stomach": "Gastroenterology",
        "digestive": "Gastroenterology",
        "abdominal": "Gastroenterology",
        "nausea": "Gastroenterology",
        "vomit": "Gastroenterology",
        "diarrhea": "Gastroenterology",
        "constipation": "Gastroenterology",
        "bowel": "Gastroenterology",
        "gastritis": "Gastroenterology",
        # Neurology
        "neurolog": "Neurology",
        "brain": "Neurology",
        "migraine": "Neurology",
        "headache": "Neurology",
        "seizure": "Neurology",
        "stroke": "Neurology",
        "parkinson": "Neurology",
        # Dermatology
        "dermat": "Dermatology",
        "skin": "Dermatology",
        "rash": "Dermatology",
        "acne": "Dermatology",
        "eczema": "Dermatology",
        # Orthopedics
        "bone": "Orthopedics",
        "fracture": "Orthopedics",
        "broke": "Orthopedics",
        "break": "Orthopedics",
        "joint": "Orthopedics",
        "sprain": "Orthopedics",
        "strain": "Orthopedics",
        "arthritis": "Orthopedics",
        "tendon": "Orthopedics",
        "ligament": "Orthopedics",
        "dislocation": "Orthopedics",
        "knee pain": "Orthopedics",
        "back pain": "Orthopedics",
        "neck pain": "Orthopedics",
        # Internal Medicine
        "infection": "Internal Medicine",
        "fever": "Internal Medicine",
        "flu": "Internal Medicine",
        "diabetes": "Internal Medicine",
        "hypertension": "Internal Medicine",
        # Other specialties
        "kidney": "Nephrology",
        "liver": "Hepatology",
        "eye": "Ophthalmology",
        "vision": "Ophthalmology",
        "ear": "Otolaryngology",
        "throat": "Otolaryngology",
        "psychiatric": "Psychiatry",
        "mental": "Psychiatry",
        "depression": "Psychiatry",
        "anxiety": "Psychiatry",
        "panic": "Psychiatry",
        "women": "Gynecology",
        "pregnancy": "Gynecology",
        "child": "Pediatrics",
    }

    combined_text = (query + " " + summary).lower()
    for keyword, specialty in specialty_keywords.items():
        if keyword in combined_text:
            return specialty

    return "General Practice"


def get_suspected_condition(
    query: str,
    summary: str,
    rag_context: str = "",
    reasoner_output: object | None = None,
) -> str:
    """
    Detect the underlying medical condition from query and summary.
    Uses RAG context (medical articles) and reasoner output when available.
    Falls back to keyword matching for robustness.
    """
    if reasoner_output is not None and hasattr(reasoner_output, "possible_conditions"):
        possible_conditions = getattr(reasoner_output, "possible_conditions")
        if possible_conditions:
            first = possible_conditions[0]
            if isinstance(first, dict):
                return first.get("name", "Unknown condition")
            return getattr(first, "name", "Unknown condition")

    combined_text = (query + " " + summary + " " + rag_context).lower()

    conditions_to_check = [
        ("myocardial infarction", "Myocardial infarction/Coronary artery disease"),
        ("acute coronary syndrome", "Myocardial infarction/Coronary artery disease"),
        ("coronary artery disease", "Myocardial infarction/Coronary artery disease"),
        ("heart attack", "Myocardial infarction/Coronary artery disease"),
        ("meningitis", "Meningitis"),
        ("pneumonia", "Pneumonia"),
        ("tuberculosis", "Tuberculosis"),
        ("asthma", "Asthma"),
        ("copd", "COPD"),
        ("stroke", "Stroke"),
        ("gastritis", "Gastritis/GERD/IBS"),
        ("gerd", "Gastritis/GERD/IBS"),
        ("ibs", "Gastritis/GERD/IBS"),
        ("appendicitis", "Appendicitis"),
        ("panic disorder", "Panic disorder"),
        ("anxiety", "Anxiety disorder"),
        ("depression", "Major depressive disorder"),
        ("migraine", "Migraine"),
        ("vertigo", "Vertigo"),
        ("neuropathy", "Neuropathy"),
        ("sepsis", "Sepsis"),
        ("malaria", "Malaria"),
        ("dengue", "Dengue fever"),
        ("influenza", "Influenza"),
        ("covid", "COVID-19"),
        ("coronavirus", "COVID-19"),
        ("cholecystitis", "Cholecystitis"),
    ]

    summary_lower = summary.lower()
    for condition_keyword, condition_name in conditions_to_check:
        if condition_keyword in summary_lower:
            logger.info(
                "condition_detected from_summary condition=%s",
                condition_name,
            )
            return condition_name

    priority_combinations = [
        (["chest pain", "left arm"], "Myocardial infarction/Coronary artery disease"),
        (["chest pain", "jaw pain"], "Myocardial infarction/Coronary artery disease"),
        (["chest pain", "radiates"], "Myocardial infarction/Coronary artery disease"),
        (["severe headache", "stiff neck"], "Meningitis"),
        (["high fever", "stiff neck"], "Meningitis"),
        (["stiff neck", "fever"], "Meningitis"),
        (["panic", "anxiety"], "Panic disorder"),
        (["panic attack"], "Panic disorder"),
        (["severe panic"], "Panic disorder"),
    ]

    for symptoms, condition in priority_combinations:
        if all(symptom in combined_text for symptom in symptoms):
            logger.info(
                "condition_detected combination=%s condition=%s",
                symptoms,
                condition,
            )
            return condition

    disease_keywords = PATIENT_SYMPTOM_KEYWORDS
    sorted_keywords = sorted(disease_keywords, key=lambda x: len(x[0]), reverse=True)

    for keyword, condition in sorted_keywords:
        if keyword in combined_text:
            logger.info(
                "condition_detected keyword=%s condition=%s",
                keyword,
                condition,
            )
            return condition

    return "Unknown condition"


def _get_age_context(age: int | None) -> str:
    """Get age-appropriate clinical context for triage."""
    if age is None:
        return ""

    if age < 1:
        return "NEONATE/INFANT - Critical: Monitor vital signs closely, fever in infants <3 months is emergency."
    elif age < 5:
        return "TODDLER/PRESCHOOL - High risk: Dehydration, airway compromise, fever. Watch for lethargy."
    elif age < 13:
        return "CHILD - Consider pediatric norms: Heart rate, respiratory rate, blood pressure vary by age."
    elif age < 18:
        return "ADOLESCENT - Consider psychosocial factors, contraception counseling if relevant."
    elif age < 65:
        return "ADULT - Standard adult presentation."
    else:
        return "GERIATRIC - Higher risk: Polypharmacy, atypical presentations, falls, cognitive changes."


def _classify_with_age(query: str, age: int | None = None) -> TriageLevel:
    """Classify urgency considering age factors."""
    level: TriageLevel = "low"

    if age is not None and age < 5:
        pedi_high_risk = (
            "fever", "stridor", "drooling", "retracting", "cyanosis",
            "lethargy", "unresponsive", "seizure", "dehydration",
            "not eating", "vomiting", "diarrhea for hours"
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


def get_suggested_doctors(
    db: Session, specialty: str, limit: int = 3
) -> list[DoctorSuggestion]:
    """Get doctors matching the recommended specialty."""
    if not db:
        return []

    try:
        doctors = (
            db.query(DoctorProfile)
            .filter(DoctorProfile.specialty.ilike(f"%{specialty.split()[0]}%"))
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
) -> TriageResponse:
    normalized_query = query.strip()
    safety_level = _safety_floor(normalized_query, age)
    triage_level = safety_level
    _spine_pain = any(t in normalized_query.lower() for t in ('back pain','back hurts','back ache','backache','neck pain','neck hurts','spine','spinal','cervical','lumbar','disc','herniated','sciatica'))
    _limb_neuro = any(t in normalized_query.lower() for t in ('numbness','tingling','numb','weakness','paresthesia','radiculopathy'))
    _bladder = any(t in normalized_query.lower() for t in ('bladder','bowel','incontinence'))
    if _spine_pain and _limb_neuro:
        _floor = 'high' if _bladder else 'medium'
        triage_level = _max_triage_level(triage_level, _floor)
    settings = get_settings()

    age_context = _get_age_context(age)
    retrieval_query = f"{normalized_query} {age_context}" if age_context else normalized_query

    candidate_top_k = max(settings.rag_top_k * RAG_CANDIDATE_MULTIPLIER, settings.rag_top_k)
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

    patient_context: str | None = None
    history_used = False
    if patient_id is not None and db is not None:
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
    elif patient_id is not None:
        patient_context = f"Patient ID {patient_id} was provided."
        history_used = True

    summary = get_reasoner().reason(
        normalized_query,
        contexts,
        triage_level,
        patient_context=patient_context,
    )
    triage_level = _max_triage_level(safety_level, summary.urgency_level)
    actions = _build_actions(triage_level)

    summary_text = summary.clinical_summary if hasattr(summary, 'clinical_summary') else str(summary)
    simple_reasoning = simplify_reasoning(summary_text)
    recommended_specialty = _normalize_recommended_specialty(
        summary.recommended_specialty
        if hasattr(summary, "recommended_specialty")
        else None,
        normalized_query,
        triage_level,
    )
    rag_context_str = " ".join(
        f"{getattr(c, 'title', '')} {getattr(c, 'text', '')[:200]}".strip()
        for c in reasoner_chunks
    )
    suspected_condition = get_suspected_condition(
        normalized_query,
        summary_text,
        rag_context_str,
        reasoner_output=summary,
    )

    suggested_doctors = (
        get_suggested_doctors(db, recommended_specialty)
        if db and recommended_specialty
        else []
    )
    confidence_score = _compute_confidence(normalized_query, chunks, summary)
    clarification_needed = needs_clarification(confidence_score, triage_level)
    clarification_questions = (
        get_clarification_questions(
            normalized_query,
            summary=summary,
            recommended_specialty=recommended_specialty,
            triage_level=triage_level,
        )
        if clarification_needed
        else []
    )

    logger.info(
        "triage_completed triage_level=%s query_length=%s contexts=%s specialty=%s condition=%s confidence=%s",
        triage_level,
        len(normalized_query),
        len(contexts),
        recommended_specialty,
        suspected_condition,
        confidence_score,
    )

    return TriageResponse(
        triage_level=triage_level,
        urgency_level=triage_level,
        confidence_score=confidence_score,
        needs_clarification=clarification_needed,
        urgency_label="High" if triage_level == "high" else "Medium" if triage_level == "medium" else "Low",
        urgency_reason=(summary.clinical_summary[:300] if hasattr(summary, 'clinical_summary') and summary.clinical_summary else ' '.join(summary.red_flags[:2]) if hasattr(summary, 'red_flags') and summary.red_flags else normalized_query),
        summary=summary_text,
        clinical_summary=summary_text,
        simple_reasoning=simple_reasoning,
        plain_language_explanation=summary.patient_friendly_explanation if hasattr(summary, 'patient_friendly_explanation') else simple_reasoning,
        patient_friendly_explanation=summary.patient_friendly_explanation if hasattr(summary, 'patient_friendly_explanation') else simple_reasoning,
        actions=summary.recommended_actions if hasattr(summary, 'recommended_actions') and summary.recommended_actions else actions,
        recommended_actions=summary.recommended_actions if hasattr(summary, 'recommended_actions') else actions,
        red_flags=summary.red_flags if hasattr(summary, 'red_flags') else [],
        recommended_specialty=recommended_specialty,
        specialty_reason=(
            f"Recommended based on the most likely condition: {recommended_specialty}."
            if recommended_specialty
            else "Recommended based on your symptoms and clinical assessment"
        ),
        suspected_condition=suspected_condition,
        suspected_conditions=[
            {
                'name': getattr(c, 'name', ''),
                'likelihood': getattr(c, 'likelihood', 'possible'),
                'explanation': getattr(c, 'explanation', ''),
            }
            for c in (summary.possible_conditions if hasattr(summary,'possible_conditions') else [])
        ],
        supporting_references=[
            {'title': c.title, 'source': c.source, 'url': c.url, 'snippet': c.text[:400] if c.text else ''}
            for c in _filter_supporting_reference_chunks(reasoner_chunks)[: settings.rag_top_k]
        ] if reasoner_chunks else [],
        suggested_doctors=suggested_doctors,
        history_used=history_used,
        questions=clarification_questions,
        disclaimer=(
            "This is not medical advice. If you think you may have a medical "
            "emergency, seek immediate care."
        ),
    )


def _compute_confidence(
    query: str,
    chunks: list,
    summary,
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
        top_score = max((getattr(c, 'score', 0) for c in chunks), default=0)
        if top_score < 0.45:
            score -= 0.25
        elif top_score < 0.55:
            score -= 0.1
    
    # Few conditions identified
    conditions = getattr(summary, 'possible_conditions', [])
    if len(conditions) < 2:
        score -= 0.2
    
    # Catch-all specialty
    if getattr(summary, 'recommended_specialty', '') == 'Internal Medicine':
        score -= 0.1
    
    return round(max(0.0, min(1.0, score)), 2)



















