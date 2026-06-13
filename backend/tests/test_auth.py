from __future__ import annotations

from uuid import uuid4


def test_register_and_login_flow(client) -> None:
    email = f"patient-{uuid4().hex}@example.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": "patient",
            "full_name": "Patient Example",
            "national_id": "30101010154321",
            "sex": "Female",
        },
    )

    assert register_response.status_code == 201
    register_payload = register_response.json()
    assert register_payload["email"] == email
    assert register_payload["role"] == "patient"

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "password123",
        },
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert login_payload["token_type"] == "bearer"
    assert login_payload["role"] == "patient"
    assert isinstance(login_payload["access_token"], str)
    assert login_payload["access_token"]
