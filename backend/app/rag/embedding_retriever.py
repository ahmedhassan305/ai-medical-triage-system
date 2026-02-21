from __future__ import annotations

import logging
import threading

import faiss
import numpy as np

from app.core.config import get_settings
from app.rag.chunking import chunk_text
from app.rag.dataset_loader import load_conditions
from app.rag.embedding_model import get_embedding_model
from app.rag.faiss_store import (
    ChunkMetadata,
    build_and_persist_index,
    load_index,
    search_index,
)
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)


class EmbeddingRetriever(Retriever):
    def __init__(
        self,
        data_dir: str,
        chunk_size: int,
        overlap: int,
        top_k: int,
    ) -> None:
        settings = get_settings()
        self.data_dir = data_dir
        self.chunk_size = max(1, chunk_size)
        self.overlap = max(0, overlap)
        self.top_k = max(1, top_k)
        self.cache_dir = settings.rag_cache_dir
        self.rebuild_index = settings.rag_rebuild_index

        self._lock = threading.Lock()
        self._ready = False
        self._index: faiss.Index | None = None
        self._metadata: list[ChunkMetadata] = []

        self._ensure_index()

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        self._ensure_index()
        if self._index is None or not self._metadata:
            return []

        model = get_embedding_model()
        query_embedding = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        query_vector = np.asarray(query_embedding, dtype=np.float32)[0]

        limit = max(1, top_k)
        hits = search_index(
            query_vector,
            limit,
            index=self._index,
            metadata=self._metadata,
        )

        contexts: list[str] = []
        for item, score in hits:
            logger.info("rag_retrieval score=%.4f title=%s", score, item["title"])
            contexts.append(self._format_context(item, score))
        return contexts

    def _ensure_index(self) -> None:
        if self._ready:
            return

        with self._lock:
            if self._ready:
                return

            if not self.rebuild_index:
                cached_index, cached_metadata = load_index(cache_dir=self.cache_dir)
                if cached_index is not None and cached_metadata:
                    self._index = cached_index
                    self._metadata = cached_metadata
                    self._ready = True
                    logger.info(
                        "rag_index_loaded cache_dir=%s documents=%s",
                        self.cache_dir,
                        len(cached_metadata),
                    )
                    return

            chunks = self._build_chunks()
            if not chunks:
                raise RuntimeError("No chunks available to build embedding index.")

            self._index, self._metadata = build_and_persist_index(
                chunks,
                cache_dir=self.cache_dir,
            )
            self._ready = True
            logger.info(
                "rag_index_built cache_dir=%s documents=%s",
                self.cache_dir,
                len(self._metadata),
            )

    def _build_chunks(self) -> list[ChunkMetadata]:
        conditions = load_conditions(self.data_dir)
        chunks: list[ChunkMetadata] = []
        for condition in conditions:
            pieces = chunk_text(condition.full_text, self.chunk_size, self.overlap)
            for piece in pieces:
                chunks.append(
                    ChunkMetadata(
                        source=condition.source,
                        title=condition.title,
                        url=condition.url,
                        chunk_text=piece,
                    )
                )
        return chunks

    def _format_context(self, item: ChunkMetadata, score: float) -> str:
        header = f"({item['source']}) {item['title']}"
        if item["url"]:
            header = f"{header} - {item['url']}"
        return f"{header}\n[score: {score:.4f}]\n{item['chunk_text']}"
