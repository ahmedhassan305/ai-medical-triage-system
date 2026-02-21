from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings
from app.model.reasoner import Reasoner, StubReasoner
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.retriever import Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.schemas.triage import TriageLevel, TriageResponse

logger = logging.getLogger(__name__)
reasoner: Reasoner = StubReasoner()

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


def clear_runtime_state() -> None:
    get_retriever.cache_clear()


def triage(query: str) -> TriageResponse:
    normalized_query = query.strip()
    triage_level = _classify(normalized_query)
    settings = get_settings()
    contexts = get_retriever().retrieve(normalized_query, top_k=settings.rag_top_k)
    summary = reasoner.reason(normalized_query, contexts, triage_level)
    actions = _build_actions(triage_level)

    logger.info(
        "triage_completed triage_level=%s query_length=%s contexts=%s",
        triage_level,
        len(normalized_query),
        len(contexts),
    )

    return TriageResponse(
        triage_level=triage_level,
        summary=summary,
        actions=actions,
        disclaimer=(
            "This is not medical advice. If you think you may have a medical "
            "emergency, seek immediate care."
        ),
    )
