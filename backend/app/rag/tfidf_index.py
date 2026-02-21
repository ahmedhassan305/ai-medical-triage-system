from __future__ import annotations

from collections.abc import Sequence

from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from app.rag.dataset_loader import MedicalCondition


def build_index(
    conditions: Sequence[MedicalCondition],
    *,
    max_features: int,
    ngram_range: tuple[int, int],
) -> tuple[TfidfVectorizer, csr_matrix]:
    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=max_features,
        ngram_range=ngram_range,
    )
    matrix = vectorizer.fit_transform(condition.full_text for condition in conditions)
    return vectorizer, matrix


def search(
    query: str,
    *,
    conditions: Sequence[MedicalCondition],
    vectorizer: TfidfVectorizer,
    matrix: csr_matrix,
    top_k: int,
) -> list[tuple[MedicalCondition, float]]:
    if not query.strip() or not conditions:
        return []

    query_vector = vectorizer.transform([query])
    scores = linear_kernel(query_vector, matrix).ravel()
    ranked_indexes = scores.argsort()[::-1][: max(top_k, 0)]
    return [(conditions[index], float(scores[index])) for index in ranked_indexes]
