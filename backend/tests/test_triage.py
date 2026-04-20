import pytest
from fastapi.testclient import TestClient

from app.db.models import Visit
from app.db.session import SessionLocal


def _auth_headers(client: TestClient, email: str, role: str) -> dict[str, str]:
    password = "password123"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": role},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("query", "expected_level"),
    [
        ("I need guidance for mild headache after work.", "low"),
        ("I have fever and nausea since last night.", "medium"),
        ("I have chest pain and shortness of breath.", "high"),
    ],
)
def test_triage_v1_happy_path(
    client: TestClient, query: str, expected_level: str
) -> None:
    res = client.post("/api/v1/triage", json={"query": query})
    assert res.status_code == 200
    payload = res.json()
    assert payload["triage_level"] == expected_level
    assert payload["urgency_level"] == expected_level
    assert isinstance(payload["summary"], str)
    assert isinstance(payload["patient_friendly_explanation"], str)
    assert isinstance(payload["actions"], list)
    assert isinstance(payload["suspected_conditions"], list)
    assert isinstance(payload["supporting_references"], list)
    assert isinstance(payload["disclaimer"], str)


def test_triage_invalid_body(client: TestClient) -> None:
    res = client.post("/api/v1/triage", json={"query": ""})
    assert res.status_code == 422
    payload = res.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."


def test_triage_legacy_route_compatibility(client: TestClient) -> None:
    res = client.post("/triage", json={"query": "I have fever and cough."})
    assert res.status_code == 200
    assert res.json()["triage_level"] == "medium"


def test_triage_with_patient_history_flag(client: TestClient) -> None:
    headers = _auth_headers(client, "history.patient@example.com", "patient")
    profile_response = client.post(
        "/api/v1/patients/me",
        headers=headers,
        json={
            "full_name": "History Patient",
            "age": 54,
            "sex": "female",
            "national_id": None,
            "current_governorate": "Giza",
            "smoker": False,
            "alcoholic": False,
            "chronic_conditions": ["hypertension"],
        },
    )
    assert profile_response.status_code == 200
    patient_id = profile_response.json()["id"]

    db = SessionLocal()
    db.add(
        Visit(
            patient_id=patient_id,
            symptoms="chest pain and shortness of breath",
            diagnosis="rule-out ACS",
            notes="Emergency referral advised",
        )
    )
    db.commit()
    db.close()

    res = client.post(
        "/api/v1/triage",
        headers=headers,
        json={"query": "I have chest pain", "patient_id": patient_id},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["history_used"] is True
    assert payload["suggested_doctors"] == []


def test_anonymous_triage_cannot_use_patient_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/triage",
        json={"query": "I have cough", "patient_id": 123},
    )
    assert response.status_code == 401
