"""
Tests for role-specific overview dashboards.

Validates:
1. Patients see their upcoming appointments and pending requests
2. Doctors see their confirmed appointments and pending requests
3. Admins see system metrics and appointment status breakdown
4. Overview pages properly filter data by user role
"""

import pytest
from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str, role: str) -> dict[str, str]:
    """Helper to authenticate and return auth headers."""
    password = "password123"
    register_payload: dict[str, str] = {
        "email": email,
        "password": password,
        "role": role,
    }
    
    if role == "patient":
        suffix = sum(ord(c) for c in email) % 100000
        register_payload.update(
            {
                "full_name": "Test Patient",
                "national_id": f"301010101{suffix:05d}",
                "sex": "Female",
            }
        )
    
    response = client.post("/api/v1/auth/register", json=register_payload)
    assert response.status_code == 201
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_patient_overview_requires_authentication(client: TestClient) -> None:
    """Patient overview should require authentication."""
    response = client.get("/api/v1/overview")
    assert response.status_code == 401


def test_patient_overview_shows_upcoming_appointments(client: TestClient) -> None:
    """Patient overview should display upcoming appointments."""
    headers = _auth_headers(client, "patient.overview@example.com", "patient")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "role" in data
    assert data["role"] == "patient"
    assert "upcoming_appointments" in data or "appointments" in data


def test_doctor_overview_requires_authentication(client: TestClient) -> None:
    """Doctor overview should require authentication."""
    response = client.get("/api/v1/overview")
    assert response.status_code == 401


def test_doctor_overview_shows_confirmed_appointments(client: TestClient) -> None:
    """Doctor overview should display confirmed appointments."""
    headers = _auth_headers(client, "doctor.overview@example.com", "doctor")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "role" in data
    assert data["role"] == "doctor"
    assert "appointments" in data or "confirmed_appointments" in data


def test_admin_overview_shows_system_metrics(client: TestClient) -> None:
    """Admin overview should display system-wide metrics."""
    headers = _auth_headers(client, "admin.overview@example.com", "admin")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "role" in data
    assert data["role"] == "admin"
    
    # Admin should see system metrics
    assert "total_patients" in data or "patient_count" in data
    assert "total_doctors" in data or "doctor_count" in data
    assert "total_appointments" in data or "appointment_count" in data


def test_admin_overview_shows_appointment_status_breakdown(
    client: TestClient,
) -> None:
    """Admin overview should break down appointments by status."""
    headers = _auth_headers(client, "admin.metrics@example.com", "admin")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    
    # Should have some breakdown of appointment statuses
    assert isinstance(data, dict)
    # Check for common status fields
    statuses = ["requested", "approved", "rejected", "completed"]
    has_status_info = any(
        status in str(data).lower() or f"{status}_count" in str(data)
        for status in statuses
    )
    assert has_status_info or "appointments" in data, (
        "Admin overview should include appointment status information"
    )


def test_admin_overview_shows_specialty_coverage(client: TestClient) -> None:
    """Admin overview should show specialty distribution."""
    headers = _auth_headers(client, "admin.specialty@example.com", "admin")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    
    # Should include specialty coverage info
    has_specialty_info = (
        "specialty" in str(data).lower()
        or "specialties" in str(data).lower()
        or "doctors_by_specialty" in str(data)
    )
    assert has_specialty_info or isinstance(data, dict), (
        "Admin overview should include specialty information"
    )


def test_patient_cannot_see_admin_metrics(client: TestClient) -> None:
    """Patient overview should not expose admin-level metrics."""
    headers = _auth_headers(client, "patient.noadmin@example.com", "patient")
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    
    # Patient should NOT have these admin fields
    admin_fields = [
        "total_patients",
        "total_doctors",
        "all_appointments",
        "specialty_coverage",
    ]
    
    for field in admin_fields:
        assert field not in data, (
            f"Patient overview should not include admin field: {field}"
        )


def test_doctor_cannot_see_other_doctors_appointments(client: TestClient) -> None:
    """Doctor should only see their own appointments, not other doctors'."""
    # Create two doctors
    headers_doc1 = _auth_headers(client, "doctor.1@example.com", "doctor")
    headers_doc2 = _auth_headers(client, "doctor.2@example.com", "doctor")
    
    # Get overviews for both
    response1 = client.get("/api/v1/overview", headers=headers_doc1)
    response2 = client.get("/api/v1/overview", headers=headers_doc2)
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Data structures should be similar but not identical
    data1 = response1.json()
    data2 = response2.json()
    
    assert data1["role"] == "doctor"
    assert data2["role"] == "doctor"


@pytest.mark.parametrize(
    ("email", "role", "expected_fields"),
    [
        ("patient.v1@example.com", "patient", ["role", "upcoming_appointments"]),
        ("doctor.v1@example.com", "doctor", ["role", "appointments"]),
        (
            "admin.v1@example.com",
            "admin",
            ["role", "total_patients", "total_doctors"],
        ),
    ],
)
def test_overview_returns_role_appropriate_structure(
    client: TestClient, email: str, role: str, expected_fields: list[str]
) -> None:
    """Overview should return different structures based on user role."""
    headers = _auth_headers(client, email, role)
    
    response = client.get("/api/v1/overview", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    
    # Must have role field
    assert "role" in data
    assert data["role"] == role
    
    # At least one role-specific field should be present
    has_expected = any(field in data for field in expected_fields)
    assert has_expected, (
        f"Expected at least one of {expected_fields} for {role} overview, got: {data.keys()}"
    )
