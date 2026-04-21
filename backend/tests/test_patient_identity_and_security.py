from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.egyptian_national_id import parse_egyptian_national_id


def _register_and_login(
    client: TestClient,
    *,
    email: str,
    role: str,
) -> dict[str, str]:
    password = "password123"
    register_payload: dict[str, str] = {
        "email": email,
        "password": password,
        "role": role,
    }
    if role == "patient":
        suffix = sum(ord(character) for character in email) % 100000
        register_payload.update(
            {
                "full_name": f"Patient {suffix}",
                "national_id": f"301010101{suffix:05d}",
                "sex": "Female",
            }
        )
    register_response = client.post(
        "/api/v1/auth/register",
        json=register_payload,
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_patient_profile(
    client: TestClient,
    headers: dict[str, str],
    *,
    full_name: str,
    age: int,
    sex: str,
    national_id: str | None = None,
    current_governorate: str | None = None,
) -> dict:
    response = client.post(
        "/api/v1/patients/me",
        headers=headers,
        json={
            "full_name": full_name,
            "age": age,
            "sex": sex,
            "national_id": national_id,
            "current_governorate": current_governorate,
            "smoker": False,
            "alcoholic": False,
            "chronic_conditions": [],
        },
    )
    assert response.status_code == 200
    return response.json()


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
            "clinic": "Test Clinic",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_parse_egyptian_national_id_valid() -> None:
    parsed = parse_egyptian_national_id("30101010112345")
    assert parsed.date_of_birth.isoformat() == "2001-01-01"
    assert parsed.inferred_governorate_code == "01"
    assert parsed.inferred_governorate == "Cairo"


def test_parse_egyptian_national_id_invalid_length() -> None:
    try:
        parse_egyptian_national_id("3010101011234")
    except ValueError as exc:
        assert "14 digits" in str(exc)
    else:
        raise AssertionError("Expected invalid national ID length to raise ValueError.")


def test_parse_egyptian_national_id_invalid_date() -> None:
    try:
        parse_egyptian_national_id("30113320112345")
    except ValueError as exc:
        assert "birth date" in str(exc)
    else:
        raise AssertionError("Expected invalid date to raise ValueError.")


def test_parse_egyptian_national_id_unknown_governorate() -> None:
    try:
        parse_egyptian_national_id("30101019912345")
    except ValueError as exc:
        assert "governorate code" in str(exc)
    else:
        raise AssertionError("Expected unsupported governorate to raise ValueError.")


def test_patient_profile_derives_birth_date_and_governorate(client: TestClient) -> None:
    headers = _register_and_login(
        client,
        email="national-id-patient@example.com",
        role="patient",
    )
    payload = _create_patient_profile(
        client,
        headers,
        full_name="National ID Patient",
        age=12,
        sex="female",
        national_id="30101010167890",
        current_governorate="",
    )
    assert payload["age"] >= 20
    assert payload["date_of_birth"] == "2001-01-01"
    assert payload["inferred_governorate_code"] == "01"
    assert payload["inferred_governorate"] == "Cairo"
    assert payload["current_governorate"] == "Cairo"


def test_doctor_can_create_and_lookup_patient_by_national_id(
    client: TestClient,
) -> None:
    doctor_headers = _register_and_login(
        client,
        email="managed-patient-doctor@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers,
        full_name="Managed Patient Doctor",
        specialty="Internal Medicine",
    )

    create_response = client.post(
        "/api/v1/patients/",
        headers=doctor_headers,
        json={
            "full_name": "Mona Adel",
            "sex": "Female",
            "national_id": "30101010254321",
            "current_governorate": "",
            "smoker": False,
            "alcoholic": False,
            "chronic_conditions": ["Asthma"],
        },
    )
    assert create_response.status_code == 201
    created_patient = create_response.json()
    assert created_patient["date_of_birth"] == "2001-01-01"
    assert created_patient["inferred_governorate"] == "Alexandria"
    assert created_patient["current_governorate"] == "Alexandria"

    lookup_response = client.get(
        "/api/v1/patients/by-national-id/30101010254321",
        headers=doctor_headers,
    )
    assert lookup_response.status_code == 200
    assert lookup_response.json()["id"] == created_patient["id"]


def test_managed_patient_create_rejects_invalid_sex(client: TestClient) -> None:
    admin_headers = _register_and_login(
        client,
        email="managed-patient-admin@example.com",
        role="admin",
    )

    create_response = client.post(
        "/api/v1/patients/",
        headers=admin_headers,
        json={
            "full_name": "Invalid Sex Profile",
            "sex": "Unknown",
            "national_id": "30101010133333",
            "current_governorate": "Cairo",
            "smoker": False,
            "alcoholic": False,
            "chronic_conditions": [],
        },
    )
    assert create_response.status_code == 422


def test_patient_cannot_use_other_patient_history_in_triage(client: TestClient) -> None:
    headers_one = _register_and_login(
        client,
        email="owner-a@example.com",
        role="patient",
    )
    patient_one = _create_patient_profile(
        client,
        headers_one,
        full_name="Owner A",
        age=32,
        sex="male",
    )

    headers_two = _register_and_login(
        client,
        email="owner-b@example.com",
        role="patient",
    )
    patient_two = _create_patient_profile(
        client,
        headers_two,
        full_name="Owner B",
        age=29,
        sex="female",
    )

    response = client.post(
        "/api/v1/triage",
        headers=headers_one,
        json={"query": "I have cough", "patient_id": patient_two["id"]},
    )
    assert response.status_code == 403
    assert patient_one["id"] != patient_two["id"]


def test_appointments_are_filtered_by_owner_and_doctor_restrictions(
    client: TestClient,
) -> None:
    patient_headers_one = _register_and_login(
        client,
        email="appointments-a@example.com",
        role="patient",
    )
    patient_one = _create_patient_profile(
        client,
        patient_headers_one,
        full_name="Appointments A",
        age=44,
        sex="female",
    )

    patient_headers_two = _register_and_login(
        client,
        email="appointments-b@example.com",
        role="patient",
    )
    patient_two = _create_patient_profile(
        client,
        patient_headers_two,
        full_name="Appointments B",
        age=41,
        sex="male",
    )

    doctor_headers_one = _register_and_login(
        client,
        email="doctor-a@example.com",
        role="doctor",
    )
    doctor_one = _create_doctor_profile(
        client,
        doctor_headers_one,
        full_name="Doctor A",
        specialty="Pulmonology",
    )

    doctor_headers_two = _register_and_login(
        client,
        email="doctor-b@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers_two,
        full_name="Doctor B",
        specialty="Pulmonology",
    )

    create_first = client.post(
        "/api/v1/appointments/",
        headers=patient_headers_one,
        json={
            "patient_id": patient_one["id"],
            "doctor_id": doctor_one["id"],
            "reason": "Cough review",
        },
    )
    assert create_first.status_code == 200
    first_appointment_id = create_first.json()["id"]

    create_second = client.post(
        "/api/v1/appointments/",
        headers=patient_headers_two,
        json={
            "patient_id": patient_two["id"],
            "doctor_id": doctor_one["id"],
            "reason": "Fever review",
        },
    )
    assert create_second.status_code == 200

    patient_one_list = client.get("/api/v1/appointments/", headers=patient_headers_one)
    assert patient_one_list.status_code == 200
    assert len(patient_one_list.json()) == 1
    assert patient_one_list.json()[0]["patient_id"] == patient_one["id"]

    doctor_list = client.get("/api/v1/appointments/", headers=doctor_headers_one)
    assert doctor_list.status_code == 200
    assert len(doctor_list.json()) == 2

    forbidden_status = client.patch(
        f"/api/v1/appointments/{first_appointment_id}/status",
        headers=doctor_headers_two,
        json={"status": "approved"},
    )
    assert forbidden_status.status_code == 403


def test_patient_can_only_view_own_visits(client: TestClient) -> None:
    patient_headers_one = _register_and_login(
        client,
        email="visits-a@example.com",
        role="patient",
    )
    patient_one = _create_patient_profile(
        client,
        patient_headers_one,
        full_name="Visits A",
        age=28,
        sex="female",
    )

    patient_headers_two = _register_and_login(
        client,
        email="visits-b@example.com",
        role="patient",
    )
    patient_two = _create_patient_profile(
        client,
        patient_headers_two,
        full_name="Visits B",
        age=30,
        sex="male",
    )

    doctor_headers = _register_and_login(
        client,
        email="visit-doctor@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers,
        full_name="Visit Doctor",
        specialty="Internal Medicine",
    )

    create_visit_response = client.post(
        "/api/v1/visits/",
        headers=doctor_headers,
        json={
            "patient_id": patient_two["id"],
            "symptoms": "Fever and cough",
            "diagnosis": "Upper respiratory infection",
        },
    )
    assert create_visit_response.status_code == 200

    forbidden = client.get(
        f"/api/v1/visits/patient/{patient_two['id']}",
        headers=patient_headers_one,
    )
    assert forbidden.status_code == 403

    own_visits = client.get(
        f"/api/v1/visits/patient/{patient_one['id']}",
        headers=patient_headers_one,
    )
    assert own_visits.status_code == 200
    assert own_visits.json() == []


def test_doctor_and_admin_workspace_visit_listing_is_role_filtered(
    client: TestClient,
) -> None:
    patient_headers = _register_and_login(
        client,
        email="workspace-visits-patient@example.com",
        role="patient",
    )
    patient = _create_patient_profile(
        client,
        patient_headers,
        full_name="Workspace Patient",
        age=31,
        sex="female",
    )

    doctor_headers_one = _register_and_login(
        client,
        email="workspace-doctor-one@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers_one,
        full_name="Workspace Doctor One",
        specialty="Neurology",
    )

    doctor_headers_two = _register_and_login(
        client,
        email="workspace-doctor-two@example.com",
        role="doctor",
    )
    _create_doctor_profile(
        client,
        doctor_headers_two,
        full_name="Workspace Doctor Two",
        specialty="Internal Medicine",
    )

    admin_headers = _register_and_login(
        client,
        email="workspace-admin@example.com",
        role="admin",
    )

    first_visit = client.post(
        "/api/v1/visits/",
        headers=doctor_headers_one,
        json={
            "patient_id": patient["id"],
            "symptoms": "Headache and nausea",
            "diagnosis": "Needs neurological review",
        },
    )
    assert first_visit.status_code == 200

    second_visit = client.post(
        "/api/v1/visits/",
        headers=doctor_headers_two,
        json={
            "patient_id": patient["id"],
            "symptoms": "Fever and fatigue",
            "diagnosis": "General medical assessment",
        },
    )
    assert second_visit.status_code == 200

    doctor_one_workspace = client.get("/api/v1/visits/", headers=doctor_headers_one)
    assert doctor_one_workspace.status_code == 200
    assert len(doctor_one_workspace.json()) == 1
    assert doctor_one_workspace.json()[0]["diagnosis"] == "Needs neurological review"

    doctor_two_workspace = client.get("/api/v1/visits/", headers=doctor_headers_two)
    assert doctor_two_workspace.status_code == 200
    assert len(doctor_two_workspace.json()) == 1
    assert doctor_two_workspace.json()[0]["diagnosis"] == "General medical assessment"

    admin_workspace = client.get("/api/v1/visits/", headers=admin_headers)
    assert admin_workspace.status_code == 200
    admin_diagnoses = {visit["diagnosis"] for visit in admin_workspace.json()}
    assert "Needs neurological review" in admin_diagnoses
    assert "General medical assessment" in admin_diagnoses
