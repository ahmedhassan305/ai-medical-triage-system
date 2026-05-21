from __future__ import annotations

import os

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.model.reasoner import OllamaReasoner
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
    candidate_names = {
        item.get("name")
        for item in models
        if isinstance(item, dict) and item.get("name")
    }
    return model in candidate_names or f"{model}:latest" in candidate_names


def test_triage_reasoner_mode_stub(monkeypatch) -> None:
    monkeypatch.setenv("REASONER_MODE", "stub")
    monkeypatch.setenv("RAG_RETRIEVER", "stub")
    monkeypatch.setenv("STRICT_REASONER", "false")
    get_settings.cache_clear()
    clear_runtime_state()

    with TestClient(create_app()) as client:
        response = client.post("/api/v1/triage", json={"query": "I have headache"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["patient_friendly_explanation"]
    assert payload["urgency_level"] == "low"
    assert isinstance(payload["suspected_conditions"], list)


def test_ollama_mode_unavailable_returns_503_without_keyword_fallback(monkeypatch) -> None:
    monkeypatch.setenv("REASONER_MODE", "ollama")
    monkeypatch.setenv("RAG_RETRIEVER", "stub")
    monkeypatch.setenv("STRICT_REASONER", "false")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    monkeypatch.setenv("OLLAMA_MODEL", "missing-model")
    get_settings.cache_clear()
    clear_runtime_state()

    with TestClient(create_app()) as client:
        response = client.post(
            "/api/v1/triage",
            json={"query": "I have chest pain and shortness of breath."},
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["message"] == (
        "The triage AI system is unresponsive right now. Please try again shortly."
    )


def test_triage_reasoner_mode_ollama_when_available(monkeypatch) -> None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
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
    payload = response.json()
    assert payload["summary"].strip()
    assert payload["patient_friendly_explanation"].strip()


def test_first_reasoner_prompt_discourages_unsupported_cardiac_overreach() -> None:
    prompt = OllamaReasoner(model="test-model")._build_prompt(
        query="I have fever, trouble breathing, and fatigue.",
        contexts=[],
        triage_level="high",
        patient_context=None,
    )

    assert "Smoking alone is not enough" in prompt
    assert "Fever plus trouble breathing" in prompt
    assert "Do NOT include Myocardial infarction" in prompt
    assert "preliminary best-fit specialty" in prompt
