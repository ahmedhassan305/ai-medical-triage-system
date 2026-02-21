from __future__ import annotations

import logging
import threading

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from app.rag.dataset_loader import MedicalCondition, load_conditions
from app.rag.retriever import Retriever
from app.rag.tfidf_index import build_index, search

logger = logging.getLogger(__name__)


class TfidfRetriever(Retriever):
    def __init__(
        self,
        data_dir: str,
        max_features: int,
        ngram_range: tuple[int, int],
    ) -> None:
        self.data_dir = data_dir
        self.max_features = max_features
        self.ngram_range = ngram_range
        self._lock = threading.Lock()
        self._conditions: list[MedicalCondition] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix: csr_matrix | None = None

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        self._ensure_index()
        if not self._conditions or self._vectorizer is None or self._matrix is None:
            return []

        results = search(
            query,
            conditions=self._conditions,
            vectorizer=self._vectorizer,
            matrix=self._matrix,
            top_k=top_k,
        )
        return [self._format_context(condition) for condition, _score in results]

    def _ensure_index(self) -> None:
        if self._vectorizer is not None and self._matrix is not None:
            return

        with self._lock:
            if self._vectorizer is not None and self._matrix is not None:
                return
            try:
                self._conditions = load_conditions(self.data_dir)
                if not self._conditions:
                    return
                self._vectorizer, self._matrix = build_index(
                    self._conditions,
                    max_features=self.max_features,
                    ngram_range=self.ngram_range,
                )
            except Exception:
                logger.exception("tfidf_index_build_failed data_dir=%s", self.data_dir)
                self._conditions = []
                self._vectorizer = None
                self._matrix = None

    def _format_context(self, condition: MedicalCondition) -> str:
        header = f"({condition.source}) {condition.title}"
        if condition.url:
            header = f"{header} - {condition.url}"

        context_text = condition.full_text
        if len(context_text) > 600:
            context_text = f"{context_text[:600].rstrip()}..."
        return f"{header}\n{context_text}"
