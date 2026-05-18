from __future__ import annotations

from datetime import time

from fastapi.testclient import TestClient

from app.db.models import DoctorProfile
from app.db.session import SessionLocal
from app.services.lab_pdf_extraction import extract_lab_values_from_text
from app.services.slot_booking import ensure_demo_availability_for_all_doctors

PASSWORD = "password123"


def _register_and_login(client: TestClient, email: str, role: str) -> dict[str, str]:
    payload: dict[str, str] = {"email": email, "password": PASSWORD, "role": role}
    if role == "patient":
        suffix = sum(ord(character) for character in email) % 100000
        payload.update(
            {
                "full_name": f"Patient {suffix}",
                "national_id": f"301010101{suffix:05d}",
                "sex": "Female",
            }
        )
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_doctor(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/doctors/me",
        headers=headers,
        json={
            "full_name": "Schedule Doctor",
            "specialty": "Cardiology",
            "clinic": "Demo Heart Clinic",
            "area": "Smouha",
            "city": "Alexandria",
        },
    )
    assert response.status_code == 200
    return response.json()


def _my_patient(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get("/api/v1/patients/me", headers=headers)
    assert response.status_code == 200
    return response.json()


def test_structured_history_endpoint_and_triage_context(client: TestClient) -> None:
    headers = _register_and_login(client, "history-patient@example.com", "patient")
    patient = _my_patient(client, headers)

    created = client.post(
        f"/api/v1/patients/{patient['id']}/medical-history",
        headers=headers,
        json={
            "category": "surgery",
            "title": "Appendectomy",
            "status": "resolved",
            "notes": "Surgery in childhood",
        },
    )
    assert created.status_code == 201

    listed = client.get(
        f"/api/v1/patients/{patient['id']}/medical-history",
        headers=headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "Appendectomy"

    triage = client.post(
        "/api/v1/triage",
        headers=headers,
        json={
            "query": "I have abdominal pain",
            "patient_id": patient["id"],
        },
    )
    assert triage.status_code == 200
    assert triage.json()["history_used"] is True


def test_lab_pdf_extraction_and_upload(client: TestClient) -> None:
    headers = _register_and_login(client, "lab-patient@example.com", "patient")
    patient = _my_patient(client, headers)
    values = extract_lab_values_from_text("Hb 12.4 g/dL WBC 8.1 Platelets 250")
    assert {value.lab_name for value in values} >= {"Hemoglobin", "WBC", "Platelets"}

    pdf_bytes = b"%PDF-1.4\nHb 12.4 g/dL WBC 8.1 Platelets 250\n%%EOF"
    response = client.post(
        "/api/v1/triage/lab-pdf/extract",
        headers=headers,
        data={"patient_id": str(patient["id"])},
        files={"file": ("labs.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["values"]

    rejected = client.post(
        "/api/v1/triage/lab-pdf/extract",
        headers=headers,
        files={"file": ("labs.txt", b"Hb 12", "text/plain")},
    )
    assert rejected.status_code == 422


def test_admin_can_edit_doctor_and_schedule(client: TestClient) -> None:
    admin_headers = _register_and_login(client, "schedule-admin@example.com", "admin")
    doctor_headers = _register_and_login(client, "schedule-doc@example.com", "doctor")
    doctor = _create_doctor(client, doctor_headers)

    updated = client.patch(
        f"/api/v1/doctors/{doctor['id']}",
        headers=admin_headers,
        json={
            "full_name": "Updated Doctor",
            "specialty": "Chest Diseases",
            "clinic": "Updated Clinic",
            "area": "Roushdy",
            "city": "Alexandria",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Doctor"

    schedule = client.post(
        f"/api/v1/doctors/{doctor['id']}/schedules",
        headers=admin_headers,
        json={
            "day_of_week": "sunday",
            "start_time": "09:00:00",
            "end_time": "11:00:00",
            "slot_minutes": 30,
            "location_label": "Updated Clinic",
            "is_active": True,
        },
    )
    assert schedule.status_code == 201

    schedules = client.get(
        f"/api/v1/doctors/{doctor['id']}/schedules",
        headers=admin_headers,
    )
    assert schedules.status_code == 200
    assert schedules.json()[0]["start_time"] == "09:00:00"


def test_availability_seed_is_idempotent(client: TestClient) -> None:
    _register_and_login(client, "seed-doc@example.com", "doctor")
    db = SessionLocal()
    try:
        doctor = (
            db.query(DoctorProfile)
            .filter(DoctorProfile.full_name.like("Patient%").is_(False))
            .first()
        )
        if doctor is None:
            doctor = DoctorProfile(
                full_name="Seeded Availability Doctor",
                specialty="Pediatrics",
                clinic="Seed Clinic",
                area="Gleem",
                city="Alexandria",
            )
            db.add(doctor)
            db.commit()
        first = ensure_demo_availability_for_all_doctors(db)
        second = ensure_demo_availability_for_all_doctors(db)
        assert first >= 0
        assert second == 0
        assert all(
            schedule.start_time in {time(9, 0), time(14, 0)}
            for schedule in doctor.schedules
        )
    finally:
        db.close()
