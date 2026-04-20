import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB_PATH = Path(tempfile.gettempdir()) / "aimts_friend_branch_test.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://localhost:3000"
os.environ["REASONER_MODE"] = "stub"
os.environ["RAG_RETRIEVER"] = "stub"
os.environ["RAG_REBUILD_INDEX"] = "false"
os.environ["DB_AUTO_CREATE"] = "true"

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rag.embedding_model import clear_embedding_model_cache  # noqa: E402
from app.services.triage_service import clear_runtime_state  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    clear_runtime_state()
    clear_embedding_model_cache()

    with TestClient(create_app()) as test_client:
        yield test_client
