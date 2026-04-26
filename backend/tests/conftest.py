# ruff: noqa: E402

import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

TEST_DB_PATH = Path(tempfile.gettempdir()) / "ai_medical_triage_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["DB_AUTO_CREATE"] = "true"

from app.core.config import get_settings
from app.db.session import engine
from app.main import create_app
from app.rag.embedding_model import clear_embedding_model_cache
from app.services.triage_service import clear_runtime_state


@pytest.fixture
def client() -> TestClient:
    os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
    os.environ["REASONER_MODE"] = "stub"
    os.environ["RAG_RETRIEVER"] = "stub"
    os.environ["RAG_REBUILD_INDEX"] = "false"
    get_settings.cache_clear()
    clear_runtime_state()
    clear_embedding_model_cache()

    with TestClient(create_app()) as test_client:
        yield test_client

    engine.dispose()
    TEST_DB_PATH.unlink(missing_ok=True)
