import pytest
from fastapi.testclient import TestClient

from app.db.models import Visit
from app.db.session import SessionLocal
from app.schemas.triage import ReasonerCondition, StructuredReasoningOutput


def _auth_headers(client: TestClient, email: str, role: str) -> dict[str, str]:
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
                "full_name": "Test Patient",
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
    assert isinstance(payload["suggested_doctors"], list)


def test_anonymous_triage_cannot_use_patient_context(client: TestClient) -> None:
    response = client.post(
        "/api/v1/triage",
        json={"query": "I have cough", "patient_id": 123},
    )
    assert response.status_code == 401


def test_triage_asks_plain_language_clarification_questions(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/triage",
        json={"query": "I have stomach pain"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["needs_clarification"] is True
    question_text = " ".join(question["question"] for question in payload["questions"])
    lowered = question_text.lower()
    assert "gastroenterology" not in lowered
    assert "dyspnea" not in lowered
    assert "neurological" not in lowered


def test_unsupported_reasoner_high_is_reconciled_to_medium(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnsupportedHighReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="high",
                clinical_summary=(
                    "Headache, eye pain, and nausea need more evaluation."
                ),
                patient_friendly_explanation=(
                    "More detail is needed before deciding how urgent this is."
                ),
                possible_conditions=[
                    ReasonerCondition(
                        name="Migraine",
                        explanation="Headache with nausea can fit migraine.",
                    )
                ],
                recommended_specialty="Ophthalmology",
                recommended_actions=["Schedule an eye exam."],
                red_flags=["eye pain", "headache"],
                clinical_features={
                    "chief_complaint": "headache",
                    "symptoms": ["headache"],
                    "body_systems": ["neurologic", "eye"],
                    "red_flags_present": ["eye pain", "headache"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: UnsupportedHighReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "my head aches and my eyes hurt and i feel nauseous"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency_level"] == "medium"
    assert payload["needs_clarification"] is True
    assert payload["recommended_actions"][0].startswith("Consider urgent care")
    assert payload["red_flags"] == []


def test_supported_high_urgency_remains_high(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SupportedHighReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="high",
                clinical_summary="Chest pain with breathing trouble is concerning.",
                patient_friendly_explanation="This may be serious.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Acute coronary syndrome",
                        explanation="Chest pain with breathing trouble can be serious.",
                    )
                ],
                recommended_specialty="Cardiology",
                recommended_actions=["Seek emergency care now."],
                red_flags=["shortness of breath"],
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: SupportedHighReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have chest pain and shortness of breath."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency_level"] == "high"
    assert payload["needs_clarification"] is False


def test_llm_invented_sudden_headache_does_not_create_high_urgency(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InventedSuddenHeadacheReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="low",
                clinical_summary="Headache with eye pain and nausea needs review.",
                patient_friendly_explanation="More detail is needed.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Migraine",
                        explanation="Headache with nausea can fit migraine.",
                    )
                ],
                recommended_specialty="Neurology",
                recommended_actions=["Book a medical review."],
                red_flags=["eye pain"],
                clinical_features={
                    "chief_complaint": "headache",
                    "symptoms": ["headache", "eye pain", "nausea"],
                    "body_systems": ["neurologic"],
                    "onset": "sudden",
                    "red_flags_present": ["eye pain"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: InventedSuddenHeadacheReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "my head aches and my eyes hurt and i feel nauseous"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency_level"] != "high"
