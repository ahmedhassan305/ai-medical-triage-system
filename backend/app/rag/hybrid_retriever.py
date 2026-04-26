from __future__ import annotations

import math
import re

from app.core.config import get_settings
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.retriever import RetrievedChunk, Retriever
from app.rag.tfidf_retriever import TfidfRetriever


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


class HybridRetriever(Retriever):
    def __init__(
        self,
        *,
        data_dir: str,
        max_features: int,
        ngram_range: tuple[int, int],
        chunk_size: int,
        overlap: int,
        top_k: int,
    ) -> None:
        settings = get_settings()
        self.top_k = top_k
        self.dense_weight = settings.rag_dense_weight
        self.sparse_weight = settings.rag_sparse_weight
        self.rerank_weight = settings.rag_rerank_weight
        self.source_priorities = settings.rag_source_priorities
        self._dense = EmbeddingRetriever(
            data_dir=data_dir,
            chunk_size=chunk_size,
            overlap=overlap,
            top_k=top_k,
        )
        self._sparse = TfidfRetriever(
            data_dir=data_dir,
            max_features=max_features,
            ngram_range=ngram_range,
        )

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        return [
            self._format_context(chunk) for chunk in self.retrieve_chunks(query, top_k)
        ]

    def retrieve_chunks(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        limit = max(1, top_k)
        dense_hits = self._dense.retrieve_chunks(query, top_k=limit * 3)
        sparse_hits = self._sparse.retrieve_chunks(query, top_k=limit * 3)
        merged: dict[str, tuple[RetrievedChunk, float]] = {}

        sparse_denominator = max(1, len(sparse_hits))

        for rank, chunk in enumerate(dense_hits, start=1):
            score = self._normalize(chunk.score)
            combined = (
                (self.dense_weight * score)
                + (0.15 / (rank + 1))
                + self._source_bonus(chunk)
            )
            merged[chunk.chunk_id] = (chunk, combined)

        for rank, chunk in enumerate(sparse_hits, start=1):
            score = max(0.0, 1.0 - ((rank - 1) / sparse_denominator))
            existing = merged.get(chunk.chunk_id)
            combined = (
                (self.sparse_weight * score)
                + (0.15 / (rank + 1))
                + self._source_bonus(chunk)
            )
            if existing is None or combined > existing[1]:
                merged[chunk.chunk_id] = (chunk, combined)
            else:
                merged[chunk.chunk_id] = (existing[0], existing[1] + combined)

        query_tokens = _tokenize(query)
        reranked: list[RetrievedChunk] = []
        for chunk, score in merged.values():
            lexical = self._lexical_overlap(query_tokens, chunk.text)
            final_score = score + (self.rerank_weight * lexical)
            reranked.append(
                RetrievedChunk(
                    doc_id=chunk.doc_id,
                    source_file=chunk.source_file,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    source=chunk.source,
                    title=chunk.title,
                    url=chunk.url,
                    score=round(final_score, 4),
                )
            )

        reranked.sort(key=lambda item: item.score, reverse=True)

        deduped: list[RetrievedChunk] = []
        seen_docs: set[str] = set()
        for chunk in reranked:
            dedupe_key = f"{chunk.doc_id}:{chunk.text[:120]}"
            if dedupe_key in seen_docs:
                continue
            seen_docs.add(dedupe_key)
            deduped.append(chunk)
            if len(deduped) >= limit:
                break
        return deduped

    def _lexical_overlap(self, query_tokens: set[str], text: str) -> float:
        if not query_tokens:
            return 0.0
        text_tokens = _tokenize(text)
        if not text_tokens:
            return 0.0
        return len(query_tokens.intersection(text_tokens)) / len(query_tokens)

    def _source_bonus(self, chunk: RetrievedChunk) -> float:
        return 0.05 * self.source_priorities.get(chunk.source, 1.0)

    def _normalize(self, value: float) -> float:
        return 1 / (1 + math.exp(-value))

    def _format_context(self, chunk: RetrievedChunk) -> str:
        header = f"({chunk.source}) {chunk.title}"
        if chunk.url:
            header = f"{header} - {chunk.url}"
        return f"{header}\n[score: {chunk.score:.4f}]\n{chunk.text}"
