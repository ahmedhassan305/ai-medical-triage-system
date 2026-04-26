from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db.models import PatientProfile, User, Visit
from app.db.session import SessionLocal


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
    assert isinstance(payload["summary"], str)
    assert isinstance(payload["actions"], list)
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
    db = SessionLocal()
    user = User(
        email=f"history-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    patient = PatientProfile(
        user_id=user.id,
        full_name="History Patient",
        age=54,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=["hypertension"],
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    patient_id = patient.id
    db.add(
        Visit(
            patient_id=patient_id,
            symptoms="chest pain and shortness of breath",
            diagnosis="rule-out ACS",
            notes="Emergency referral advised",
        )
    )
    db.commit()
    token = create_access_token(str(user.id), user.role)
    db.close()

    res = client.post(
        "/api/v1/triage",
        json={"query": "I have chest pain", "patient_id": patient_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["history_used"] is True


def test_triage_history_endpoint_returns_saved_session(client: TestClient) -> None:
    db = SessionLocal()
    user = User(
        email=f"triage-history-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    token = create_access_token(str(user.id), user.role)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have fever and cough"},
        headers=headers,
    )
    assert response.status_code == 200
    triage_session_id = response.json()["triage_session_id"]
    assert triage_session_id is not None

    history = client.get("/api/v1/triage/history", headers=headers)
    assert history.status_code == 200
    payload = history.json()
    assert payload["total"] >= 1
    history_item = next(
        item for item in payload["items"] if item["id"] == triage_session_id
    )
    assert history_item["confidence"] == response.json()["confidence"]

    detail = client.get(f"/api/v1/triage/{triage_session_id}", headers=headers)
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["result"]["triage_session_id"] == triage_session_id
    assert detail_payload["result"]["confidence"] == response.json()["confidence"]
    assert detail_payload["result"]["red_flags"] == response.json()["red_flags"]
