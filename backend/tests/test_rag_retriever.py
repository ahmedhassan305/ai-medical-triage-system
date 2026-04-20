from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.rag.retriever import StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever
from app.services import triage_service


def _fixture_data_dir() -> str:
    return str(Path(__file__).resolve().parent / "fixtures")


def test_api_v1_triage_with_tfidf_has_summary(monkeypatch) -> None:
    monkeypatch.setenv("RAG_RETRIEVER", "tfidf")
    monkeypatch.setenv("RAG_DATA_DIR", _fixture_data_dir())
    monkeypatch.setenv("RAG_TOP_K", "2")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")

    get_settings.cache_clear()
    triage_service.clear_runtime_state()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/triage", json={"query": "I have fever and cough"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]
    assert body["supporting_references"]
    assert body["suspected_conditions"]


def test_tfidf_retriever_context_has_source_and_url() -> None:
    retriever = TfidfRetriever(
        data_dir=_fixture_data_dir(),
        max_features=1000,
        ngram_range=(1, 2),
    )

    contexts = retriever.retrieve("chest pain with breathing issues", top_k=2)
    assert contexts
    assert any("(Mayo Clinic)" in context or "(NHS)" in context for context in contexts)
    assert any("https://" in context for context in contexts)


def test_tfidf_retriever_chunks_include_metadata() -> None:
    retriever = TfidfRetriever(
        data_dir=_fixture_data_dir(),
        max_features=1000,
        ngram_range=(1, 2),
    )
    chunks = retriever.retrieve_chunks("flu fever dry cough", top_k=2)
    assert chunks
    first = chunks[0]
    assert first.doc_id
    assert first.source_file.endswith(".json")
    assert first.chunk_id
    assert first.text


def test_missing_data_dir_falls_back_to_stub(monkeypatch, tmp_path) -> None:
    missing_dir = tmp_path / "missing_dataset"
    monkeypatch.setenv("RAG_RETRIEVER", "tfidf")
    monkeypatch.setenv("RAG_DATA_DIR", str(missing_dir))
    monkeypatch.setenv("RAG_TOP_K", "3")

    get_settings.cache_clear()
    triage_service.clear_runtime_state()

    retriever = triage_service.get_retriever()
    assert isinstance(retriever, StubRetriever)

    response = triage_service.triage("I have mild discomfort and a cough.")
    assert response.summary
