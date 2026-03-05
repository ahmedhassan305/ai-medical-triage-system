from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import PatientProfile, Visit


@dataclass(frozen=True)
class PatientContextResult:
    history_used: bool
    context_text: str
    matched_visit_ids: list[int]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def _similarity(query: str, symptoms: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    symptom_tokens = _tokenize(symptoms)
    if not symptom_tokens:
        return 0.0
    return len(query_tokens.intersection(symptom_tokens)) / len(query_tokens)


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
        ranked = sorted(
            ((visit, _similarity(query, visit.symptoms)) for visit in visits),
            key=lambda item: item[1],
            reverse=True,
        )
        top = ranked[: self.top_matches]

        demographics = (
            f"Patient demographics: age={patient.age}, sex={patient.sex}, "
            f"smoker={patient.smoker}, alcoholic={patient.alcoholic}, "
            "chronic_conditions="
            f"{', '.join(patient.chronic_conditions or []) or 'none'}."
        )

        visit_lines: list[str] = []
        matched_ids: list[int] = []
        for visit, score in top:
            matched_ids.append(visit.id)
            visit_lines.append(
                "Visit #{id} similarity={score:.2f} symptoms={symptoms} "
                "diagnosis={diagnosis} notes={notes}".format(
                    id=visit.id,
                    score=score,
                    symptoms=visit.symptoms,
                    diagnosis=visit.diagnosis or "n/a",
                    notes=visit.notes or "n/a",
                )
            )

        context_text = demographics
        if visit_lines:
            context_text = f"{context_text}\nRelevant history:\n" + "\n".join(
                visit_lines
            )

        return PatientContextResult(
            history_used=True,
            context_text=context_text,
            matched_visit_ids=matched_ids,
        )
