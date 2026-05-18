from __future__ import annotations

import logging

import numpy as np

from app.rag.embedding_model import get_embedding_model
from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)


def rerank_retrieved_chunks(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    limit: int,
    min_score: float = 0.32,
    relative_floor: float = 0.82,
) -> list[RetrievedChunk]:
    if not chunks:
        return []

    try:
        return _semantic_rerank(
            query,
            chunks,
            limit=limit,
            min_score=min_score,
            relative_floor=relative_floor,
        )
    except Exception:
        logger.exception("rag_rerank_failed fallback=original_order")
        return _dedupe_chunks(chunks)[:limit]


def _semantic_rerank(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    limit: int,
    min_score: float,
    relative_floor: float,
) -> list[RetrievedChunk]:
    model = get_embedding_model()
    candidate_texts = [_candidate_text(chunk) for chunk in chunks]
    embeddings = model.encode(
        [query, *candidate_texts],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    vectors = np.asarray(embeddings, dtype=np.float32)
    query_vector = vectors[0]
    candidate_vectors = vectors[1:]
    semantic_scores = candidate_vectors @ query_vector

    rescored: list[tuple[RetrievedChunk, float]] = []
    for chunk, semantic_score in zip(chunks, semantic_scores, strict=False):
        original_score = max(0.0, min(1.0, float(getattr(chunk, "score", 0.0))))
        combined_score = (0.8 * float(semantic_score)) + (0.2 * original_score)
        rescored.append(
            (
                RetrievedChunk(
                    doc_id=chunk.doc_id,
                    source_file=chunk.source_file,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    source=chunk.source,
                    title=chunk.title,
                    url=chunk.url,
                    score=combined_score,
                ),
                combined_score,
            )
        )

    ordered = sorted(rescored, key=lambda item: item[1], reverse=True)
    deduped = _dedupe_chunks([chunk for chunk, _score in ordered])
    if not deduped:
        return []

    best_score = deduped[0].score
    floor = max(min_score, best_score * relative_floor)
    filtered = [chunk for chunk in deduped if chunk.score >= floor]
    logger.info(
        "rag_reranked candidates=%s kept=%s best_score=%.4f floor=%.4f",
        len(chunks),
        len(filtered[:limit]),
        best_score,
        floor,
    )
    return filtered[:limit]


def _candidate_text(chunk: RetrievedChunk) -> str:
    text = chunk.text
    if len(text) > 1200:
        text = text[:1200]
    return f"{chunk.title}. {text}"


def _dedupe_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[str] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in chunks:
        key = (chunk.title or chunk.doc_id).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
    return deduped
