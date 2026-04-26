from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.config import get_settings
from app.rag.embedding_model import get_embedding_model
from app.schemas.triage import TriageDecision, TriageLevel

LEVEL_ORDER: dict[TriageLevel, int] = {"low": 0, "medium": 1, "high": 2}

LEVEL_PROTOTYPES: dict[TriageLevel, tuple[str, ...]] = {
    "low": (
        "mild headache after work with no warning signs",
        "minor sore throat and rest advice",
        "seasonal allergy symptoms with no breathing distress",
    ),
    "medium": (
        "fever and vomiting with worsening dehydration risk",
        "migraine symptoms with persistent pain and nausea",
        "infection symptoms needing urgent clinic review",
    ),
    "high": (
        "chest pain with shortness of breath and emergency concern",
        "stroke symptoms with facial droop and urgent emergency response",
        "severe bleeding or overdose requiring emergency care now",
    ),
}

RED_FLAG_TERMS: tuple[str, ...] = (
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "seizure",
    "stroke",
    "unconscious",
    "severe bleeding",
    "overdose",
    "suicidal",
    "confusion",
    "blue lips",
)


@dataclass(frozen=True)
class ClassificationSignals:
    heuristic_level: TriageLevel
    embedding_level: TriageLevel
    llm_level: TriageLevel | None
    final_level: TriageLevel
    confidence: float
    explanation: str
    red_flags: list[str]


class HybridTriageClassifier:
    def assess(
        self,
        *,
        query: str,
        heuristic_level: TriageLevel,
        llm_level: TriageLevel | None,
        contexts: list[str],
        patient_context: str | None,
    ) -> ClassificationSignals:
        embedding_level, embedding_score = self._embedding_signal(query)
        red_flags = self._extract_red_flags(query, contexts, patient_context)

        signal_levels = [heuristic_level, embedding_level]
        if llm_level is not None:
            signal_levels.append(llm_level)
        final_level = max(signal_levels, key=self._score_level)

        if red_flags:
            final_level = "high"

        confidence = self._confidence(
            heuristic_level=heuristic_level,
            embedding_level=embedding_level,
            llm_level=llm_level,
            final_level=final_level,
            embedding_score=embedding_score,
            red_flag_count=len(red_flags),
        )
        explanation = self._build_explanation(
            heuristic_level=heuristic_level,
            embedding_level=embedding_level,
            llm_level=llm_level,
            final_level=final_level,
            red_flags=red_flags,
            embedding_score=embedding_score,
        )

        return ClassificationSignals(
            heuristic_level=heuristic_level,
            embedding_level=embedding_level,
            llm_level=llm_level,
            final_level=final_level,
            confidence=confidence,
            explanation=explanation,
            red_flags=red_flags,
        )

    def to_decision(self, signals: ClassificationSignals) -> TriageDecision:
        return TriageDecision(
            heuristic_level=signals.heuristic_level,
            embedding_level=signals.embedding_level,
            llm_level=signals.llm_level,
            final_level=signals.final_level,
            confidence=signals.confidence,
            explanation=signals.explanation,
        )

    def _embedding_signal(self, query: str) -> tuple[TriageLevel, float]:
        settings = get_settings()
        if not settings.triage_enable_embedding_signal:
            return "low", 0.5

        try:
            model = get_embedding_model()
            prototype_texts = [
                text for items in LEVEL_PROTOTYPES.values() for text in items
            ]
            embeddings = model.encode(
                [query, *prototype_texts],
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            query_vector = np.asarray(embeddings[0], dtype=np.float32)
            cursor = 1
            best_level: TriageLevel = "low"
            best_score = -1.0
            for level, examples in LEVEL_PROTOTYPES.items():
                level_vectors = np.asarray(
                    embeddings[cursor : cursor + len(examples)],
                    dtype=np.float32,
                )
                cursor += len(examples)
                score = float(np.max(level_vectors @ query_vector))
                if score > best_score:
                    best_level = level
                    best_score = score
            return best_level, max(0.0, min(1.0, (best_score + 1.0) / 2.0))
        except Exception:
            return "low", 0.5

    def _extract_red_flags(
        self,
        query: str,
        contexts: list[str],
        patient_context: str | None,
    ) -> list[str]:
        combined = " ".join([query, patient_context or ""]).lower()
        found = [term for term in RED_FLAG_TERMS if term in combined]
        return list(dict.fromkeys(found))

    def _confidence(
        self,
        *,
        heuristic_level: TriageLevel,
        embedding_level: TriageLevel,
        llm_level: TriageLevel | None,
        final_level: TriageLevel,
        embedding_score: float,
        red_flag_count: int,
    ) -> float:
        signals = [heuristic_level, embedding_level]
        if llm_level is not None:
            signals.append(llm_level)
        agreement = sum(1 for level in signals if level == final_level) / len(signals)
        confidence = 0.45 + (agreement * 0.35) + (embedding_score * 0.15)
        if red_flag_count:
            confidence += 0.05
        return max(0.35, min(0.98, round(confidence, 2)))

    def _build_explanation(
        self,
        *,
        heuristic_level: TriageLevel,
        embedding_level: TriageLevel,
        llm_level: TriageLevel | None,
        final_level: TriageLevel,
        red_flags: list[str],
        embedding_score: float,
    ) -> str:
        parts = [
            f"Rules suggested {heuristic_level}.",
            "Embedding similarity suggested "
            f"{embedding_level} (score={embedding_score:.2f}).",
        ]
        if llm_level is not None:
            parts.append(f"LLM suggested {llm_level}.")
        if red_flags:
            parts.append(f"Detected red flags: {', '.join(red_flags[:4])}.")
        parts.append(f"Final severity was validated as {final_level}.")
        return " ".join(parts)

    def _score_level(self, level: TriageLevel) -> int:
        return LEVEL_ORDER[level]
