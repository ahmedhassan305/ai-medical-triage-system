from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import User
from app.model.reasoner import OllamaReasoner, Reasoner, StubReasoner
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.retriever import RetrievedChunk, Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.repositories.triage_repository import TriageRepository
from app.schemas.triage import (
    TriageDetail,
    TriageHistoryPage,
    TriageLevel,
    TriageResponse,
    TriageSource,
)
from app.services.patient_context import PatientContextProvider
from app.services.triage_classifier import HybridTriageClassifier

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is not medical advice. If you think you may have a medical emergency, "
    "seek immediate care."
)

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
    return any(keyword in q for keyword in keywords)


def _classify(query: str) -> TriageLevel:
    if _match_any(query, HIGH_RISK_KEYWORDS):
        return "high"
    if _match_any(query, MEDIUM_RISK_KEYWORDS):
        return "medium"
    return "low"


def _build_actions(triage_level: TriageLevel, recommended_action: str) -> list[str]:
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

    if recommended_action not in actions:
        actions.insert(0, recommended_action)
    return actions


def _chunk_to_context(chunk: RetrievedChunk) -> str:
    header = f"({chunk.source}) {chunk.title}"
    if chunk.url:
        header = f"{header} - {chunk.url}"
    return f"{header}\n[score: {chunk.score:.4f}]\n{chunk.text}"


def _chunks_to_sources(chunks: list[RetrievedChunk]) -> list[TriageSource]:
    return [
        TriageSource(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            source=chunk.source,
            title=chunk.title,
            url=chunk.url,
            score=chunk.score,
        )
        for chunk in chunks
    ]


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

    if settings.rag_retriever == "hybrid":
        try:
            return HybridRetriever(
                data_dir=str(data_dir),
                max_features=settings.tfidf_max_features,
                ngram_range=(settings.tfidf_ngram_min, settings.tfidf_ngram_max),
                chunk_size=settings.rag_chunk_size,
                overlap=settings.rag_chunk_overlap,
                top_k=settings.rag_top_k,
            )
        except Exception:
            logger.exception("hybrid_retriever_initialization_failed fallback=stub")
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


def triage(
    query: str,
    patient_id: int | None = None,
    db: Session | None = None,
    current_user: User | None = None,
    client_host: str | None = None,
) -> TriageResponse:
    normalized_query = query.strip()
    settings = get_settings()
    classifier = HybridTriageClassifier()
    repository = TriageRepository()

    heuristic_level = _classify(normalized_query)
    retrieved_chunks = get_retriever().retrieve_chunks(
        normalized_query,
        top_k=settings.rag_top_k,
    )
    contexts = [_chunk_to_context(chunk) for chunk in retrieved_chunks]
    sources = _chunks_to_sources(retrieved_chunks)

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

    preliminary_signals = classifier.assess(
        query=normalized_query,
        heuristic_level=heuristic_level,
        llm_level=None,
        contexts=contexts,
        patient_context=patient_context,
    )
    provisional_level = preliminary_signals.final_level

    reasoner_output = get_reasoner().reason(
        normalized_query,
        contexts,
        provisional_level,
        patient_context=patient_context,
    )
    final_signals = classifier.assess(
        query=normalized_query,
        heuristic_level=heuristic_level,
        llm_level=reasoner_output.suggested_level,
        contexts=contexts,
        patient_context=patient_context,
    )
    decision = classifier.to_decision(final_signals)
    response_confidence = round(
        min(0.99, (decision.confidence + reasoner_output.confidence) / 2),
        2,
    )
    response_red_flags = reasoner_output.red_flags or final_signals.red_flags
    actions = _build_actions(
        final_signals.final_level,
        reasoner_output.recommended_action,
    )

    triage_session_id: int | None = None
    if db is not None:
        triage_session_id = repository.create_triage_record(
            db,
            user_id=current_user.id if current_user else None,
            patient_id=patient_id,
            query=normalized_query,
            history_used=history_used,
            decision=decision,
            reasoner_output=reasoner_output,
            response_confidence=response_confidence,
            response_red_flags=response_red_flags,
            actions=actions,
            disclaimer=DISCLAIMER,
            sources=[source.model_dump() for source in sources],
            chunks=retrieved_chunks,
        )
        repository.log_audit(
            db,
            user_id=current_user.id if current_user else None,
            action="triage.run",
            resource_type="triage_session",
            resource_id=str(triage_session_id),
            status="success",
            ip_address=client_host,
            details={
                "triage_level": final_signals.final_level,
                "patient_id": patient_id,
                "history_used": history_used,
            },
        )

    logger.info(
        "triage_completed triage_level=%s query_length=%s contexts=%s",
        final_signals.final_level,
        len(normalized_query),
        len(retrieved_chunks),
    )

    return TriageResponse(
        triage_level=final_signals.final_level,
        summary=reasoner_output.summary,
        actions=actions,
        disclaimer=DISCLAIMER,
        history_used=history_used,
        confidence=response_confidence,
        risk_reasoning=reasoner_output.risk_reasoning,
        recommended_action=reasoner_output.recommended_action,
        red_flags=response_red_flags,
        sources=sources,
        decision=decision,
        triage_session_id=triage_session_id,
    )


def get_triage_history(
    db: Session,
    *,
    current_user: User,
    limit: int,
    offset: int,
) -> TriageHistoryPage:
    repository = TriageRepository()
    items, total = repository.list_history(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )
    return TriageHistoryPage(items=items, total=total, limit=limit, offset=offset)


def get_triage_detail(
    db: Session,
    *,
    current_user: User,
    triage_id: int,
) -> TriageDetail | None:
    repository = TriageRepository()
    session = repository.get_history_detail(
        db,
        current_user=current_user,
        triage_id=triage_id,
    )
    if session is None or session.result is None:
        return None

    return TriageDetail(
        id=session.id,
        query=session.query,
        patient_id=session.patient_id,
        user_id=session.user_id,
        created_at=session.created_at,
        result=TriageResponse(
            triage_level=session.final_level,
            summary=session.result.summary,
            actions=session.result.actions,
            disclaimer=session.result.disclaimer,
            history_used=session.history_used,
            confidence=session.result.confidence,
            risk_reasoning=session.result.risk_reasoning,
            recommended_action=session.result.recommended_action,
            red_flags=session.result.red_flags,
            sources=[
                TriageSource.model_validate(source) for source in session.result.sources
            ],
            decision=session.result.decision_payload,  # type: ignore[arg-type]
            triage_session_id=session.id,
        ),
    )
