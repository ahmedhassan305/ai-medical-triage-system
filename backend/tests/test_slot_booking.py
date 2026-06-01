from __future__ import annotations

from datetime import date, time

from fastapi.testclient import TestClient

from app.db.models import AppointmentSlot, Clinic, DoctorClinic, DoctorSchedule
from app.db.session import SessionLocal

DEFAULT_PASSWORD = "password123"


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    role: str,
) -> dict[str, str]:
    payload: dict[str, str] = {
        "email": email,
        "password": DEFAULT_PASSWORD,
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
        json={"email": email, "password": DEFAULT_PASSWORD},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_doctor_profile(
    client: TestClient, headers: dict[str, str], *, specialty: str
) -> dict:
    response = client.post(
        "/api/v1/doctors/me",
        headers=headers,
        json={
            "full_name": "Slot Doctor",
            "specialty": specialty,
            "clinic": "Alex Clinic",
            "city": "Alexandria",
            "area": "Smouha",
        },
    )
    assert response.status_code == 200
    return response.json()


def _get_my_patient_profile(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get("/api/v1/patients/me", headers=headers)
    assert response.status_code == 200
    return response.json()


def _configure_schedule(doctor_id: int, *, target_date: date) -> int:
    db = SessionLocal()
    try:
        clinic = Clinic(
            name="Alex Clinic",
            area="Smouha",
            city="Alexandria",
            is_active=True,
        )
        db.add(clinic)
        db.flush()

        doctor_clinic = DoctorClinic(
            doctor_id=doctor_id,
            clinic_id=clinic.id,
            is_primary=True,
            is_active=True,
        )
        db.add(doctor_clinic)
        db.flush()

        schedule = DoctorSchedule(
            doctor_id=doctor_id,
            doctor_clinic_id=doctor_clinic.id,
            day_of_week=target_date.strftime("%A"),
            start_time=time(9, 0),
            end_time=time(10, 0),
            slot_minutes=30,
            valid_from=target_date,
            valid_to=target_date,
            location_label="Alex Clinic",
            is_active=True,
        )
        db.add(schedule)
        db.commit()
        return clinic.id
    finally:
        db.close()


def test_doctor_slots_are_generated_from_schedule(client: TestClient) -> None:
    doctor_headers = _register_and_login(
        client,
        email="slot-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="Cardiology")
    target_date = date.today()
    _configure_schedule(doctor["id"], target_date=target_date)

    patient_headers = _register_and_login(
        client,
        email="slot-patient@example.com",
        role="patient",
    )
    response = client.get(
        f"/api/v1/doctors/{doctor['id']}/slots",
        headers=patient_headers,
        params={
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["clinic"]["name"] == "Alex Clinic"
    assert payload[0]["status"] == "open"


def test_doctor_slots_use_deterministic_demo_fallback_when_no_schedule(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="fallback-slot-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="Pediatrics")
    target_date = date(2026, 5, 18)

    patient_headers = _register_and_login(
        client,
        email="fallback-slot-patient@example.com",
        role="patient",
    )
    response = client.get(
        f"/api/v1/doctors/{doctor['id']}/slots",
        headers=patient_headers,
        params={
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 16
    assert payload[0]["start_at"] == "2026-05-18T09:00:00"
    assert payload[-1]["end_at"] == "2026-05-18T17:00:00"


def test_slot_booking_reserves_slot_and_blocks_double_booking(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="book-slot-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="Neurology")
    target_date = date.today()
    _configure_schedule(doctor["id"], target_date=target_date)

    patient_headers = _register_and_login(
        client,
        email="book-slot-patient@example.com",
        role="patient",
    )
    patient = _get_my_patient_profile(client, patient_headers)
    slots_response = client.get(
        f"/api/v1/doctors/{doctor['id']}/slots",
        headers=patient_headers,
        params={
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
    )
    assert slots_response.status_code == 200
    slot = slots_response.json()[0]

    booking_response = client.post(
        "/api/v1/appointments/",
        headers=patient_headers,
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "reason": "Need follow-up for dizziness",
            "slot_id": slot["id"],
        },
    )
    assert booking_response.status_code == 200
    booking_payload = booking_response.json()
    assert booking_payload["slot_id"] == slot["id"]
    assert booking_payload["clinic"]["name"] == "Alex Clinic"
    assert booking_payload["slot"]["status"] == "reserved"
    assert booking_payload["scheduled_for"] == slot["start_at"]

    db = SessionLocal()
    try:
        stored_slot = (
            db.query(AppointmentSlot).filter(AppointmentSlot.id == slot["id"]).first()
        )
        assert stored_slot is not None
        assert stored_slot.status == "reserved"
    finally:
        db.close()

    second_patient_headers = _register_and_login(
        client,
        email="book-slot-second-patient@example.com",
        role="patient",
    )
    second_patient = _get_my_patient_profile(client, second_patient_headers)
    second_booking_response = client.post(
        "/api/v1/appointments/",
        headers=second_patient_headers,
        json={
            "patient_id": second_patient["id"],
            "doctor_id": doctor["id"],
            "reason": "Trying to take a reserved slot",
            "slot_id": slot["id"],
        },
    )
    assert second_booking_response.status_code == 409

    approval_response = client.patch(
        f"/api/v1/appointments/{booking_payload['id']}/status",
        headers=doctor_headers,
        json={"status": "approved"},
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["slot"]["status"] == "booked"


def test_booking_slot_rejects_wrong_clinic(client: TestClient) -> None:
    doctor_headers = _register_and_login(
        client,
        email="wrong-clinic-slot-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="ENT")
    target_date = date.today()
    _configure_schedule(doctor["id"], target_date=target_date)

    patient_headers = _register_and_login(
        client,
        email="wrong-clinic-slot-patient@example.com",
        role="patient",
    )
    patient = _get_my_patient_profile(client, patient_headers)
    slots_response = client.get(
        f"/api/v1/doctors/{doctor['id']}/slots",
        headers=patient_headers,
        params={
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
    )
    assert slots_response.status_code == 200
    slot = slots_response.json()[0]

    booking_response = client.post(
        "/api/v1/appointments/",
        headers=patient_headers,
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "clinic_id": slot["clinic"]["id"] + 999,
            "reason": "Need ENT review",
            "slot_id": slot["id"],
        },
    )
    assert booking_response.status_code == 422


def test_legacy_booking_rejects_time_outside_doctor_availability(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="outside-availability-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="Cardiology")
    target_date = date.today()
    _configure_schedule(doctor["id"], target_date=target_date)

    patient_headers = _register_and_login(
        client,
        email="outside-availability-patient@example.com",
        role="patient",
    )
    patient = _get_my_patient_profile(client, patient_headers)
    response = client.post(
        "/api/v1/appointments/",
        headers=patient_headers,
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "reason": "Need review outside hours",
            "scheduled_for": f"{target_date.isoformat()}T11:00:00",
        },
    )

    assert response.status_code == 422


def test_legacy_appointment_creation_keeps_working_and_includes_clinic_info(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="legacy-booking-doctor@example.com",
        role="doctor",
    )
    doctor = _create_doctor_profile(client, doctor_headers, specialty="Dermatology")
    target_date = date.today()
    clinic_id = _configure_schedule(doctor["id"], target_date=target_date)

    patient_headers = _register_and_login(
        client,
        email="legacy-booking-patient@example.com",
        role="patient",
    )
    patient = _get_my_patient_profile(client, patient_headers)
    response = client.post(
        "/api/v1/appointments/",
        headers=patient_headers,
        json={
            "patient_id": patient["id"],
            "doctor_id": doctor["id"],
            "reason": "Skin irritation review",
            "scheduled_for": f"{target_date.isoformat()}T09:00:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["slot_id"] is None
    assert payload["clinic_id"] == clinic_id
    assert payload["clinic"]["name"] == "Alex Clinic"
