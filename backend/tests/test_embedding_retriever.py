from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.rag.embedding_model import clear_embedding_model_cache
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.retriever import StubRetriever
from app.services import triage_service


class FakeEmbeddingModel:
    def encode(
        self,
        texts: list[str],
        *,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        vectors: list[np.ndarray] = []
        for text in texts:
            vec = np.array(
                [
                    float(sum(ord(char) for char in text) % 997),
                    float(len(text)),
                    float(text.lower().count("pain") + 1),
                    float(text.lower().count("fever") + 1),
                    float(text.lower().count("cough") + 1),
                    float(text.lower().count("flu") + 1),
                ],
                dtype=np.float32,
            )
            if normalize_embeddings:
                norm = float(np.linalg.norm(vec))
                if norm > 0:
                    vec = vec / norm
            vectors.append(vec)
        return np.vstack(vectors)


def _fixture_data_dir() -> str:
    return str(Path(__file__).resolve().parent / "fixtures")


def test_embedding_retriever_builds_index_and_returns_contexts(
    monkeypatch, tmp_path
) -> None:
    cache_dir = tmp_path / "rag_cache"
    monkeypatch.setenv("RAG_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("RAG_REBUILD_INDEX", "true")
    get_settings.cache_clear()
    clear_embedding_model_cache()

    monkeypatch.setattr(
        "app.rag.embedding_model.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )
    monkeypatch.setattr(
        "app.rag.embedding_retriever.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )
    monkeypatch.setattr(
        "app.rag.faiss_store.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )

    retriever = EmbeddingRetriever(
        data_dir=_fixture_data_dir(),
        chunk_size=180,
        overlap=40,
        top_k=2,
    )

    contexts = retriever.retrieve("severe chest pain with breathing issues", top_k=2)
    assert contexts
    assert "[score:" in contexts[0]
    assert "https://" in contexts[0]
    assert "(" in contexts[0] and ")" in contexts[0]


def test_embedding_retriever_persists_and_reloads(monkeypatch, tmp_path) -> None:
    data_dir = Path(_fixture_data_dir())
    local_data_dir = tmp_path / "data"
    shutil.copytree(data_dir, local_data_dir)

    cache_dir = tmp_path / "cache"
    monkeypatch.setenv("RAG_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("RAG_REBUILD_INDEX", "true")
    get_settings.cache_clear()
    clear_embedding_model_cache()

    monkeypatch.setattr(
        "app.rag.embedding_model.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )
    monkeypatch.setattr(
        "app.rag.embedding_retriever.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )
    monkeypatch.setattr(
        "app.rag.faiss_store.get_embedding_model",
        lambda: FakeEmbeddingModel(),
    )

    first = EmbeddingRetriever(
        data_dir=str(local_data_dir),
        chunk_size=150,
        overlap=25,
        top_k=2,
    )
    first.retrieve("flu fever dry cough", top_k=2)

    assert (cache_dir / "index.faiss").exists()
    assert (cache_dir / "metadata.json").exists()

    shutil.rmtree(local_data_dir)
    monkeypatch.setenv("RAG_REBUILD_INDEX", "false")
    get_settings.cache_clear()
    clear_embedding_model_cache()

    second = EmbeddingRetriever(
        data_dir=str(local_data_dir),
        chunk_size=150,
        overlap=25,
        top_k=2,
    )
    contexts = second.retrieve("chest pain emergency", top_k=2)
    assert contexts


def test_missing_data_dir_falls_back_to_stub_for_embedding(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("RAG_RETRIEVER", "embedding")
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "missing_data"))
    monkeypatch.setenv("RAG_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("RAG_REBUILD_INDEX", "false")

    get_settings.cache_clear()
    triage_service.clear_runtime_state()
    clear_embedding_model_cache()

    retriever = triage_service.get_retriever()
    assert isinstance(retriever, StubRetriever)
