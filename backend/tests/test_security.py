from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.db.models import Appointment, DoctorProfile, PatientProfile, User
from app.db.session import SessionLocal


def test_patient_cannot_access_other_patient_visits(client: TestClient) -> None:
    db = SessionLocal()
    user = User(
        email=f"security-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    own_profile = PatientProfile(
        user_id=user.id,
        full_name="Own Patient",
        age=31,
        sex="male",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    other_profile = PatientProfile(
        full_name="Other Patient",
        age=45,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    db.add_all([own_profile, other_profile])
    db.commit()
    db.refresh(other_profile)
    token = create_access_token(str(user.id), user.role)
    db.close()

    response = client.get(
        f"/api/v1/visits/patient/{other_profile.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_patient_history_list_hides_other_patient_triage_sessions(
    client: TestClient,
) -> None:
    db = SessionLocal()
    first_user = User(
        email=f"triage-owner-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    second_user = User(
        email=f"triage-other-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add_all([first_user, second_user])
    db.commit()
    db.refresh(first_user)
    db.refresh(second_user)

    first_profile = PatientProfile(
        user_id=first_user.id,
        full_name="Owner Patient",
        age=28,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    second_profile = PatientProfile(
        user_id=second_user.id,
        full_name="Other Patient",
        age=42,
        sex="male",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    db.add_all([first_profile, second_profile])
    db.commit()
    db.refresh(second_profile)
    second_token = create_access_token(str(second_user.id), second_user.role)
    first_user_id = first_user.id
    first_user_role = first_user.role
    db.close()

    triage_response = client.post(
        "/api/v1/triage",
        json={"query": "I have fever and cough", "patient_id": second_profile.id},
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert triage_response.status_code == 200
    triage_id = triage_response.json()["triage_session_id"]

    first_token = create_access_token(str(first_user_id), first_user_role)
    history_response = client.get(
        "/api/v1/triage/history",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert history_response.status_code == 200
    assert all(item["id"] != triage_id for item in history_response.json()["items"])


def test_patient_cannot_access_other_patient_triage_detail(client: TestClient) -> None:
    db = SessionLocal()
    first_user = User(
        email=f"triage-detail-owner-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    second_user = User(
        email=f"triage-detail-other-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add_all([first_user, second_user])
    db.commit()
    db.refresh(first_user)
    db.refresh(second_user)

    second_profile = PatientProfile(
        user_id=second_user.id,
        full_name="Protected Patient",
        age=39,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    db.add(second_profile)
    db.commit()
    db.refresh(second_profile)
    second_token = create_access_token(str(second_user.id), second_user.role)
    first_user_id = first_user.id
    first_user_role = first_user.role
    db.close()

    triage_response = client.post(
        "/api/v1/triage",
        json={"query": "I have chest pain", "patient_id": second_profile.id},
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert triage_response.status_code == 200
    triage_id = triage_response.json()["triage_session_id"]

    first_token = create_access_token(str(first_user_id), first_user_role)
    detail_response = client.get(
        f"/api/v1/triage/{triage_id}",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert detail_response.status_code == 404


def test_patient_without_profile_cannot_see_anonymous_triage_history(
    client: TestClient,
) -> None:
    anonymous_triage = client.post(
        "/api/v1/triage",
        json={"query": "I have mild headache"},
    )
    assert anonymous_triage.status_code == 200
    anonymous_triage_id = anonymous_triage.json()["triage_session_id"]

    db = SessionLocal()
    user = User(
        email=f"profileless-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(str(user.id), user.role)
    db.close()

    history_response = client.get(
        "/api/v1/triage/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_response.status_code == 200
    assert all(
        item["id"] != anonymous_triage_id for item in history_response.json()["items"]
    )

    detail_response = client.get(
        f"/api/v1/triage/{anonymous_triage_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 404


def test_appointment_list_is_filtered_to_current_patient(client: TestClient) -> None:
    db = SessionLocal()
    doctor_user = User(
        email=f"appt-doctor-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="doctor",
    )
    patient_user = User(
        email=f"appt-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    other_patient_user = User(
        email=f"appt-other-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add_all([doctor_user, patient_user, other_patient_user])
    db.commit()
    db.refresh(doctor_user)
    db.refresh(patient_user)
    db.refresh(other_patient_user)

    doctor_profile = DoctorProfile(
        user_id=doctor_user.id,
        full_name="Doctor One",
        specialty="Internal Medicine",
        clinic="Clinic A",
    )
    patient_profile = PatientProfile(
        user_id=patient_user.id,
        full_name="Patient One",
        age=30,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    other_patient_profile = PatientProfile(
        user_id=other_patient_user.id,
        full_name="Patient Two",
        age=33,
        sex="male",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    db.add_all([doctor_profile, patient_profile, other_patient_profile])
    db.commit()
    db.refresh(doctor_profile)
    db.refresh(patient_profile)
    db.refresh(other_patient_profile)

    db.add_all(
        [
            Appointment(
                patient_id=patient_profile.id,
                doctor_id=doctor_profile.id,
                reason="Review blood pressure",
                status="requested",
            ),
            Appointment(
                patient_id=other_patient_profile.id,
                doctor_id=doctor_profile.id,
                reason="Other patient visit",
                status="requested",
            ),
        ]
    )
    db.commit()
    patient_user_id = patient_user.id
    patient_user_role = patient_user.role
    patient_profile_id = patient_profile.id
    db.close()

    token = create_access_token(str(patient_user_id), patient_user_role)
    response = client.get(
        "/api/v1/appointments/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["patient_id"] == patient_profile_id


def test_doctor_cannot_update_other_doctors_appointment(client: TestClient) -> None:
    db = SessionLocal()
    first_doctor_user = User(
        email=f"doctor-owner-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="doctor",
    )
    second_doctor_user = User(
        email=f"doctor-other-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="doctor",
    )
    patient_user = User(
        email=f"doctor-patient-{uuid4().hex[:8]}@example.com",
        hashed_password=get_password_hash("Password123"),
        role="patient",
    )
    db.add_all([first_doctor_user, second_doctor_user, patient_user])
    db.commit()
    db.refresh(first_doctor_user)
    db.refresh(second_doctor_user)
    db.refresh(patient_user)

    first_doctor_profile = DoctorProfile(
        user_id=first_doctor_user.id,
        full_name="Primary Doctor",
        specialty="Emergency Medicine",
        clinic="Clinic A",
    )
    second_doctor_profile = DoctorProfile(
        user_id=second_doctor_user.id,
        full_name="Secondary Doctor",
        specialty="Cardiology",
        clinic="Clinic B",
    )
    patient_profile = PatientProfile(
        user_id=patient_user.id,
        full_name="Protected Patient",
        age=41,
        sex="female",
        smoker=False,
        alcoholic=False,
        chronic_conditions=[],
    )
    db.add_all([first_doctor_profile, second_doctor_profile, patient_profile])
    db.commit()
    db.refresh(first_doctor_profile)
    db.refresh(second_doctor_profile)
    db.refresh(patient_profile)

    appointment = Appointment(
        patient_id=patient_profile.id,
        doctor_id=first_doctor_profile.id,
        reason="Review severe chest pain",
        status="requested",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    second_doctor_user_id = second_doctor_user.id
    second_doctor_user_role = second_doctor_user.role
    db.close()

    token = create_access_token(
        str(second_doctor_user_id),
        second_doctor_user_role,
    )
    response = client.patch(
        f"/api/v1/appointments/{appointment.id}/status",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
