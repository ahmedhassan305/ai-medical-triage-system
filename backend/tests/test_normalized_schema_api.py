from __future__ import annotations

import io
import json

from fastapi.testclient import TestClient

from app.db.models import MedicalHistory, PatientSymptom, TriageAssessment
from app.db.session import SessionLocal


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    role: str,
) -> dict[str, str]:
    password = "password123"
    payload: dict[str, str] = {
        "email": email,
        "password": password,
        "role": role,
    }
    if role == "patient":
        suffix = sum(ord(character) for character in email) % 100000
        payload.update(
            {
                "full_name": f"Patient {suffix}",
                "national_id": f"301010101{suffix:05d}",
                "sex": "Female",
            }
        )

    register_response = client.post("/api/v1/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_doctor_profile(
    client: TestClient,
    headers: dict[str, str],
    *,
    full_name: str,
    specialty: str,
) -> dict:
    response = client.post(
        "/api/v1/doctors/me",
        headers=headers,
        json={
            "full_name": full_name,
            "specialty": specialty,
            "clinic": "Alex Clinic",
            "city": "Alexandria",
            "area": "Smouha",
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_patient_profile(
    client: TestClient,
    headers: dict[str, str],
    *,
    full_name: str,
    sex: str,
    national_id: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/patients/me",
        headers=headers,
        json={
            "full_name": full_name,
            "age": 30,
            "sex": sex,
            "national_id": national_id,
            "current_governorate": "Alexandria",
            "smoker": False,
            "alcoholic": False,
            "chronic_conditions": [],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_doctor_listing_keeps_api_shape_and_adds_department(client: TestClient) -> None:
    doctor_headers = _register_and_login(
        client,
        email="dept-doctor@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers,
        full_name="Department Doctor",
        specialty="Cardiology",
    )

    patient_headers = _register_and_login(
        client,
        email="doctor-list-patient@example.com",
        role="patient",
    )
    doctors_response = client.get("/api/v1/doctors/", headers=patient_headers)
    assert doctors_response.status_code == 200
    payload = doctors_response.json()
    assert payload
    assert payload[0]["specialty"]
    assert "department_name" in payload[0]


def test_triage_and_records_are_persisted_into_normalized_tables(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="normalized-doctor@example.com",
        role="doctor",
    )
    doctor_profile = _create_doctor_profile(
        client,
        doctor_headers,
        full_name="Normalized Doctor",
        specialty="Cardiology",
    )

    patient_headers = _register_and_login(
        client,
        email="normalized-patient@example.com",
        role="patient",
    )
    patient_profile = _create_patient_profile(
        client,
        patient_headers,
        full_name="Normalized Patient",
        sex="Female",
    )

    appointment_response = client.post(
        "/api/v1/appointments/",
        headers=patient_headers,
        json={
            "patient_id": patient_profile["id"],
            "doctor_id": doctor_profile["id"],
            "reason": "Chest pain review",
        },
    )
    assert appointment_response.status_code == 200

    triage_response = client.post(
        "/api/v1/triage",
        headers=patient_headers,
        json={
            "query": "I have chest pain and shortness of breath",
            "patient_id": patient_profile["id"],
        },
    )
    assert triage_response.status_code == 200
    triage_payload = triage_response.json()
    assert triage_payload["suggested_doctors"]
    assert triage_payload["recommended_specialty"] == "Cardiology"

    history_response = client.get(
        f"/api/v1/triage/history/{patient_profile['id']}",
        headers=patient_headers,
    )
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert len(history_payload) == 1
    assert (
    history_payload[0]["query_text"]
    == "I have chest pain and shortness of breath"
    )


    record_file = io.BytesIO(
        json.dumps(
            [
                {
                    "symptoms": "chest pain with mild cough",
                    "diagnosis": "Needs follow-up",
                    "notes": "Imported legacy note",
                    "doctor_id": doctor_profile["id"],
                }
            ]
        ).encode("utf-8")
    )
    import_response = client.post(
        "/api/v1/records/import",
        headers=doctor_headers,
        data={"patient_id": str(patient_profile["id"])},
        files={"file": ("records.json", record_file, "application/json")},
    )
    assert import_response.status_code == 200
    assert import_response.json()["imported"] == 1

    db = SessionLocal()
    try:
        assert (
            db.query(TriageAssessment)
            .filter(TriageAssessment.patient_id == patient_profile["id"])
            .count()
            == 1
        )
        assert (
            db.query(MedicalHistory)
            .filter(MedicalHistory.patient_id == patient_profile["id"])
            .count()
            >= 1
        )
        assert (
            db.query(PatientSymptom)
            .filter(PatientSymptom.patient_id == patient_profile["id"])
            .count()
            >= 1
        )
    finally:
        db.close()
