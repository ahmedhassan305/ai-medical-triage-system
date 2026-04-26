from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import health as health_routes


def test_health(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_v1(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_health_ready(client: TestClient) -> None:
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 200
    assert res.json() == {
        "status": "ok",
        "database": True,
        "ollama": True,
    }


def test_health_ready_returns_503_when_database_check_fails(
    client: TestClient, monkeypatch
) -> None:
    def _raise() -> None:
        raise SQLAlchemyError("db unavailable")

    monkeypatch.setattr(health_routes.engine, "connect", _raise)
    res = client.get("/api/v1/health/ready")
    assert res.status_code == 503
    assert res.json()["status"] == "degraded"
    assert res.json()["database"] is False


def test_openapi_shows_v1_routes(client: TestClient) -> None:
    res = client.get("/openapi.json")
    assert res.status_code == 200
    paths = res.json()["paths"]
    assert "/api/v1/triage" in paths
    assert "/triage" not in paths
