import pytest
from fastapi.testclient import TestClient

from app.db.models import PatientProfile, Visit
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
    patient = PatientProfile(
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
    db.close()

    res = client.post(
        "/api/v1/triage",
        json={"query": "I have chest pain", "patient_id": patient_id},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["history_used"] is True
