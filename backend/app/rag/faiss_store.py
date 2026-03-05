from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import faiss
import numpy as np

from app.core.config import get_settings
from app.rag.embedding_model import get_embedding_model

INDEX_FILENAME = "index.faiss"
METADATA_FILENAME = "metadata.json"


class ChunkMetadata(TypedDict):
    doc_id: str
    source_file: str
    chunk_id: str
    source: str
    title: str
    url: str
    chunk_text: str


def build_and_persist_index(
    chunks_with_metadata: list[ChunkMetadata],
    *,
    cache_dir: str | None = None,
) -> tuple[faiss.IndexFlatIP, list[ChunkMetadata]]:
    if not chunks_with_metadata:
        raise ValueError("No chunks provided for index build.")

    model = get_embedding_model()
    texts = [chunk["chunk_text"] for chunk in chunks_with_metadata]
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    vectors = np.asarray(embeddings, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    directory = _cache_dir(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(directory / INDEX_FILENAME))

    payload = {
        "embedding_model": get_settings().rag_embed_model,
        "items": chunks_with_metadata,
    }
    (directory / METADATA_FILENAME).write_text(
        json.dumps(payload, ensure_ascii=True),
        encoding="utf-8",
    )

    return index, chunks_with_metadata


def load_index(
    *,
    cache_dir: str | None = None,
) -> tuple[faiss.Index | None, list[ChunkMetadata]]:
    directory = _cache_dir(cache_dir)
    index_path = directory / INDEX_FILENAME
    metadata_path = directory / METADATA_FILENAME

    if not index_path.exists() or not metadata_path.exists():
        return None, []

    metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    items = metadata_payload.get("items", [])
    if not isinstance(items, list):
        return None, []

    metadata: list[ChunkMetadata] = [item for item in items if _is_chunk_metadata(item)]
    if not metadata:
        return None, []

    index = faiss.read_index(str(index_path))
    return index, metadata


def search_index(
    query_embedding: np.ndarray,
    top_k: int,
    *,
    index: faiss.Index,
    metadata: list[ChunkMetadata],
) -> list[tuple[ChunkMetadata, float]]:
    if top_k <= 0 or index.ntotal == 0:
        return []

    query = np.asarray(query_embedding, dtype=np.float32)
    if query.ndim == 1:
        query = query.reshape(1, -1)

    scores, indices = index.search(query, top_k)
    results: list[tuple[ChunkMetadata, float]] = []
    for idx, score in zip(indices[0], scores[0], strict=False):
        if idx < 0 or idx >= len(metadata):
            continue
        results.append((metadata[idx], float(score)))
    return results


def _cache_dir(value: str | None) -> Path:
    if value:
        return Path(value)
    return Path(get_settings().rag_cache_dir)


def _is_chunk_metadata(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    expected_keys = {
        "doc_id",
        "source_file",
        "chunk_id",
        "source",
        "title",
        "url",
        "chunk_text",
    }
    return expected_keys.issubset(item.keys())
