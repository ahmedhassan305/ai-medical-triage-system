from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Appointment, PatientLabResult, PatientProfile, Visit
from app.rag.embedding_model import get_embedding_model


@dataclass(frozen=True)
class PatientContextResult:
    history_used: bool
    context_text: str
    matched_visit_ids: list[int]


# Synonym map for better semantic matching without embedding model
SYMPTOM_SYNONYMS: dict[str, list[str]] = {
    "back pain": [
        "spine",
        "lumbar",
        "cervical",
        "vertebr",
        "disc",
        "sciatica",
        "backache",
    ],
    "numbness": [
        "tingling",
        "pins and needles",
        "neuropathy",
        "radiculopathy",
        "paresthesia",
        "sensation loss",
    ],
    "arm": [
        "upper limb",
        "shoulder",
        "elbow",
        "wrist",
        "hand",
        "finger",
        "radial",
        "ulnar",
    ],
    "leg": ["lower limb", "hip", "knee", "ankle", "foot", "sciatic", "femoral"],
    "headache": ["migraine", "head pain", "cephalgia", "head pressure"],
    "chest pain": ["chest tightness", "angina", "cardiac", "heart pain"],
    "breathing": ["breath", "respiratory", "dyspnea", "shortness of breath"],
    "fever": ["temperature", "febrile", "pyrexia"],
    "dizziness": ["vertigo", "lightheaded", "balance", "spinning"],
    "fatigue": ["tired", "exhausted", "weakness", "lethargy"],
}


def _expand_query(query: str) -> set[str]:
    """Expand query tokens with synonyms for better recall."""
    tokens = set(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    expanded = set(tokens)
    query_lower = query.lower()
    for canonical, synonyms in SYMPTOM_SYNONYMS.items():
        canonical_tokens = set(re.findall(r"[a-zA-Z0-9]+", canonical))
        # If any canonical term token is in the query, add its synonyms
        if canonical_tokens.intersection(tokens) or canonical in query_lower:
            for synonym in synonyms:
                expanded.update(re.findall(r"[a-zA-Z0-9]+", synonym))
    return expanded


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def _similarity(query: str, symptoms: str) -> float:
    """Compute similarity with synonym expansion for better semantic recall."""
    if not query or not symptoms:
        return 0.0

    expanded_query = _expand_query(query)
    if not expanded_query:
        return 0.0

    symptom_tokens = _tokenize(symptoms)
    if not symptom_tokens:
        return 0.0

    # Jaccard over expanded token sets
    intersection = expanded_query.intersection(symptom_tokens)
    union = expanded_query.union(symptom_tokens)
    jaccard = len(intersection) / len(union) if union else 0.0

    # Bonus: exact phrase presence
    phrase_bonus = 0.0
    query_lower = query.lower()
    symptoms_lower = symptoms.lower()
    for phrase in [query_lower] + [p.strip() for p in query_lower.split("with")]:
        phrase = phrase.strip()
        if len(phrase) > 4 and phrase in symptoms_lower:
            phrase_bonus += 0.2

    return min(1.0, jaccard + phrase_bonus)


def _semantic_similarity(query: str, symptoms: str) -> float | None:
    settings = get_settings()
    if settings.rag_retriever != "embedding":
        return None
    if not query or not symptoms:
        return None

    try:
        model = get_embedding_model()
        vectors = model.encode(
            [query, symptoms],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        matrix = np.asarray(vectors, dtype=np.float32)
        return float(matrix[0] @ matrix[1])
    except Exception:
        return None


def _hybrid_similarity(query: str, symptoms: str) -> float:
    lexical = _similarity(query, symptoms)
    semantic = _semantic_similarity(query, symptoms)
    if semantic is None:
        return lexical
    semantic = max(0.0, min(1.0, semantic))
    return round((0.35 * lexical) + (0.65 * semantic), 4)


def _chronic_condition_relevance(
    query: str, chronic_conditions: list[str]
) -> list[str]:
    """Return chronic conditions relevant to the current query."""
    if not chronic_conditions:
        return []
    query_tokens = _expand_query(query)
    relevant = []
    for condition in chronic_conditions:
        condition_tokens = _tokenize(condition)
        if condition_tokens.intersection(query_tokens):
            relevant.append(condition)
    return relevant


class PatientContextProvider:
    def __init__(self, visit_limit: int = 10, top_matches: int = 3) -> None:
        self.visit_limit = max(1, visit_limit)
        self.top_matches = max(1, top_matches)

    def build(self, db: Session, patient_id: int, query: str) -> PatientContextResult:
        patient = (
            db.query(PatientProfile).filter(PatientProfile.id == patient_id).first()
        )
        if patient is None:
            return PatientContextResult(
                history_used=False,
                context_text="Patient profile not found.",
                matched_visit_ids=[],
            )

        visits = (
            db.query(Visit)
            .filter(Visit.patient_id == patient_id)
            .order_by(Visit.created_at.desc())
            .limit(self.visit_limit)
            .all()
        )
        appointments = (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient_id)
            .order_by(Appointment.requested_at.desc())
            .limit(5)
            .all()
        )
        history_entries = list(patient.structured_history or [])[:10]
        lab_results = (
            db.query(PatientLabResult)
            .filter(PatientLabResult.patient_id == patient_id)
            .order_by(PatientLabResult.uploaded_at.desc())
            .limit(12)
            .all()
        )

        # Score visits using expanded similarity
        ranked = sorted(
            (
                (visit, _hybrid_similarity(query, visit.symptoms or ""))
                for visit in visits
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        top = ranked[: self.top_matches]

        # Build demographics block — highlight risk factors relevant to the query
        chronic = patient.chronic_conditions or []
        relevant_chronic = _chronic_condition_relevance(query, chronic)
        all_chronic_str = ", ".join(chronic) if chronic else "none"
        relevant_chronic_str = (
            f" [RELEVANT TO CURRENT COMPLAINT: {', '.join(relevant_chronic)}]"
            if relevant_chronic
            else ""
        )

        risk_factors = []
        if patient.smoker:
            risk_factors.append("smoker")
        if patient.alcoholic:
            risk_factors.append("alcohol use")

        demographics = (
            f"=== PATIENT PROFILE ===\n"
            f"Age: {patient.age} | Sex: {patient.sex} | "
            f"Location: {patient.current_governorate or 'unknown'}\n"
            f"Risk factors: {', '.join(risk_factors) or 'none'}\n"
            f"Chronic conditions: {all_chronic_str}{relevant_chronic_str}"
        )

        visit_lines: list[str] = []
        matched_ids: list[int] = []

        for visit, score in top:
            if score < 0.01 and visit.symptoms:
                # Still include the most recent visit even if low similarity,
                # so the LLM has some recency context
                pass
            matched_ids.append(visit.id)
            date_str = (
                visit.created_at.strftime("%Y-%m-%d")
                if visit.created_at
                else "unknown date"
            )
            visit_lines.append(
                f"  - [{date_str}] (relevance={score:.2f})\n"
                f"    Symptoms: {visit.symptoms or 'n/a'}\n"
                f"    Diagnosis: {visit.diagnosis or 'n/a'}\n"
                f"    Notes: {visit.notes or 'n/a'}"
            )

        context_parts = [demographics]
        if history_entries:
            context_parts.append(
                "=== STRUCTURED PATIENT HISTORY ===\n"
                + "\n".join(
                    (
                        f"  - {entry.category}: {entry.title}"
                        f" ({entry.status or 'status unknown'})"
                        f" | Notes: {entry.notes or 'n/a'}"
                    )
                    for entry in history_entries
                )
            )
        if lab_results:
            context_parts.append(
                "=== RECENT LAB VALUES ===\n"
                + "\n".join(
                    (f"  - {lab.lab_name}: {lab.value}" f" {lab.unit or ''}".strip())
                    for lab in lab_results
                )
            )
        if appointments:
            context_parts.append(
                "=== RECENT APPOINTMENT CONTEXT ===\n"
                + "\n".join(
                    (
                        f"  - Appointment #{appointment.id}: "
                        f"{appointment.status}, "
                        f"{appointment.reason}"
                    )
                    for appointment in appointments
                )
            )
        if visit_lines:
            context_parts.append(
                "=== RELEVANT MEDICAL HISTORY ===\n"
                "Use the following past visits to inform urgency and differential "
                "diagnosis. Recurrence of similar symptoms or a known chronic "
                "condition matching the "
                "complaint should raise clinical concern.\n" + "\n".join(visit_lines)
            )
        else:
            context_parts.append("=== MEDICAL HISTORY ===\nNo prior visits on record.")

        context_text = "\n\n".join(context_parts)

        return PatientContextResult(
            history_used=True,
            context_text=context_text,
            matched_visit_ids=matched_ids,
        )
