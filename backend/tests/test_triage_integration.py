from __future__ import annotations

import os

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.triage_service import clear_runtime_state


def _ollama_reachable(host: str) -> bool:
    try:
        response = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def _ollama_model_available(host: str, model: str) -> bool:
    try:
        response = httpx.get(f"{host.rstrip('/')}/api/tags", timeout=2.0)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return False

    models = payload.get("models", [])
    return any(item.get("name") == model for item in models if isinstance(item, dict))


def test_triage_reasoner_mode_stub(monkeypatch) -> None:
    monkeypatch.setenv("REASONER_MODE", "stub")
    monkeypatch.setenv("RAG_RETRIEVER", "stub")
    monkeypatch.setenv("STRICT_REASONER", "false")
    get_settings.cache_clear()
    clear_runtime_state()

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/triage", json={"query": "I have headache"})

    assert response.status_code == 200
    summary = response.json()["summary"]
    assert summary.startswith("Triage level:")


def test_triage_reasoner_mode_ollama_when_available(monkeypatch) -> None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4")
    if not _ollama_reachable(host):
        pytest.skip("Ollama is not reachable; skipping integration test.")
    if not _ollama_model_available(host, model):
        pytest.skip(
            f"Ollama model {model} is not available; skipping integration test."
        )

    monkeypatch.setenv("REASONER_MODE", "ollama")
    monkeypatch.setenv("RAG_RETRIEVER", "stub")
    monkeypatch.setenv("STRICT_REASONER", "false")
    monkeypatch.setenv("OLLAMA_HOST", host)
    monkeypatch.setenv("OLLAMA_MODEL", model)
    get_settings.cache_clear()
    clear_runtime_state()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/triage",
            json={"query": "I have chest pain with cough"},
        )

    assert response.status_code == 200
    summary = response.json()["summary"].strip()
    assert summary
    assert not summary.startswith("Triage level:")
