import pytest
from fastapi.testclient import TestClient

from app.db.models import Visit
from app.db.session import SessionLocal
from app.schemas.triage import (
    ClinicalFeatures,
    ReasonerCondition,
    StructuredReasoningOutput,
)
from app.services.triage_service import VALID_SPECIALTIES


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


def test_reasoner_watch_for_red_flags_do_not_support_high_urgency(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class WatchForRedFlagsReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="high",
                clinical_summary=(
                    "Fever, cough, and mild breathing trouble may fit infection."
                ),
                patient_friendly_explanation="You should be checked soon.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Acute Bronchitis",
                        explanation="Cough and fever can fit this.",
                    )
                ],
                recommended_specialty="Pulmonology",
                recommended_actions=["Seek urgent medical attention."],
                red_flags=["blue lips", "coughing up blood"],
                clinical_features=ClinicalFeatures(
                    chief_complaint="cough",
                    symptoms=["cough", "fever", "breathing difficulty"],
                    body_systems=["respiratory"],
                    severity="moderate",
                    red_flags_present=[],
                ),
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: WatchForRedFlagsReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have fever cough and mild trouble breathing"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["urgency_level"] == "medium"
    assert payload["red_flags"] == []
    assert payload["recommended_actions"][0].startswith("Consider urgent care")


def test_respiratory_cases_route_to_pulmonology(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RespiratoryReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="medium",
                clinical_summary="Cough with wheezing may fit asthma or bronchitis.",
                patient_friendly_explanation=(
                    "Your cough and wheezing may be related to your breathing tubes."
                ),
                possible_conditions=[
                    ReasonerCondition(
                        name="Asthma exacerbation",
                        explanation="Wheezing and cough can fit asthma.",
                    )
                ],
                recommended_specialty="Pulmonary medicine",
                recommended_actions=["Arrange a same-day medical review."],
                red_flags=[],
                clinical_features={
                    "chief_complaint": "cough",
                    "symptoms": ["cough", "breathing difficulty"],
                    "body_systems": ["respiratory"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: RespiratoryReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have cough and wheezing and trouble breathing"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_specialty"] == "Pulmonology"
    assert payload["recommended_specialty"] in VALID_SPECIALTIES


def test_unsupported_specialty_is_normalized_to_allowed_seed_specialty(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class UnsupportedSpecialtyReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="low",
                clinical_summary="Thirst and frequent urination need routine review.",
                patient_friendly_explanation="These symptoms should be checked.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Diabetes mellitus",
                        explanation="Thirst and frequent urination can fit diabetes.",
                    )
                ],
                recommended_specialty="Endocrinology",
                recommended_actions=["Book a routine medical review."],
                red_flags=[],
                clinical_features={
                    "chief_complaint": "thirst",
                    "symptoms": ["fatigue"],
                    "body_systems": ["general"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: UnsupportedSpecialtyReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I am very thirsty and peeing a lot"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_specialty"] == "Internal Medicine"
    assert payload["recommended_specialty"] in VALID_SPECIALTIES


def test_respiratory_evidence_overrides_reasoner_cardiology_drift(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CardiologyDriftReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="high",
                clinical_summary=(
                    "Chest tightness with breathing trouble may reflect a lung problem."
                ),
                patient_friendly_explanation=(
                    "This breathing trouble needs prompt care."
                ),
                possible_conditions=[
                    ReasonerCondition(
                        name="Pleurisy",
                        explanation=(
                            "Pain or tightness with breathing can fit pleurisy."
                        ),
                    ),
                    ReasonerCondition(
                        name="Asthma exacerbation",
                        explanation="Wheezing and chest tightness can fit asthma.",
                    ),
                ],
                recommended_specialty="Cardiology",
                recommended_actions=["Seek urgent care now."],
                red_flags=["difficulty breathing"],
                clinical_features={
                    "chief_complaint": "breathing difficulty",
                    "symptoms": ["chest discomfort", "breathing difficulty"],
                    "body_systems": ["cardiac", "respiratory"],
                    "red_flags_present": ["breathing distress"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: CardiologyDriftReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have chest tightness and difficulty breathing with wheezing"},
    )
    assert response.status_code == 200
    assert response.json()["recommended_specialty"] == "Pulmonology"


def test_true_heart_pattern_still_routes_to_cardiology(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class HeartPatternReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="high",
                clinical_summary=(
                    "Chest pressure with sweating may be a heart emergency."
                ),
                patient_friendly_explanation="This could be serious.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Acute coronary syndrome",
                        explanation="Chest pressure with sweating can fit this.",
                    )
                ],
                recommended_specialty="Pulmonology",
                recommended_actions=["Seek emergency care now."],
                red_flags=["chest pressure with sweating"],
                clinical_features={
                    "chief_complaint": "chest discomfort",
                    "symptoms": ["chest discomfort", "breathing difficulty"],
                    "body_systems": ["cardiac", "respiratory"],
                    "red_flags_present": ["possible heart emergency"],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: HeartPatternReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have chest pressure with sweating and shortness of breath"},
    )
    assert response.status_code == 200
    assert response.json()["recommended_specialty"] == "Cardiology"


def test_musculoskeletal_back_pain_overrides_internal_medicine(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InternalMedicineBackPainReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="low",
                clinical_summary=(
                    "Back pain after strain most likely fits muscle strain."
                ),
                patient_friendly_explanation="This sounds like a back strain.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Muscle or Ligament Strain",
                        explanation="Pain started after exercise.",
                    )
                ],
                recommended_specialty="Internal Medicine",
                recommended_actions=["Use gentle movement and follow up if worse."],
                red_flags=[],
                clinical_features={
                    "chief_complaint": "back pain",
                    "symptoms": ["back pain"],
                    "body_systems": ["musculoskeletal"],
                    "red_flags_present": [],
                },
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: InternalMedicineBackPainReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "bad back pain after exercise no numbness no weakness"},
    )
    assert response.status_code == 200
    assert response.json()["recommended_specialty"] == "Orthopedics"


def test_llm_feature_extractor_context_can_guide_specialty_adjudication(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RespiratoryFeatureExtractor:
        def extract(self, *, query, local_features, patient_context=None):
            return ClinicalFeatures(
                chief_complaint="breathing difficulty",
                symptoms=["breathing difficulty", "cough"],
                body_systems=["respiratory"],
                onset="recent",
                severity="moderate",
                missing_critical_details=[],
            )

    class CardiologyDriftReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="medium",
                clinical_summary="Breathing symptoms may reflect a lung condition.",
                patient_friendly_explanation=(
                    "Your breathing symptoms should be checked."
                ),
                possible_conditions=[
                    ReasonerCondition(
                        name="Bronchitis",
                        explanation="Cough and breathing difficulty can fit this.",
                    )
                ],
                recommended_specialty="Cardiology",
                recommended_actions=["Arrange medical review."],
                red_flags=[],
            )

    monkeypatch.setattr(
        "app.services.triage_service.get_clinical_feature_extractor",
        lambda: RespiratoryFeatureExtractor(),
    )
    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: CardiologyDriftReasoner(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "my breathing feels off and I keep coughing"},
    )

    assert response.status_code == 200
    assert response.json()["recommended_specialty"] == "Pulmonology"


def test_specialty_adjudicator_fast_path_skips_matching_body_system_case(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MatchingRespiratoryReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="medium",
                clinical_summary=(
                    "Cough and breathing difficulty fit a respiratory illness."
                ),
                patient_friendly_explanation="This may be a breathing infection.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Acute Bronchitis",
                        explanation="Cough and breathing difficulty can fit this.",
                    )
                ],
                recommended_specialty="Pulmonology",
                recommended_actions=["Arrange medical review."],
                red_flags=[],
                clinical_features=ClinicalFeatures(
                    chief_complaint="cough",
                    symptoms=["cough", "breathing difficulty"],
                    body_systems=["respiratory"],
                ),
            )

    class ShouldNotBeCalledAdjudicator:
        def adjudicate(self, **kwargs):
            raise AssertionError("adjudicator should be skipped for coherent specialty")

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: MatchingRespiratoryReasoner(),
    )
    monkeypatch.setattr(
        "app.services.triage_service.get_specialty_adjudicator",
        lambda: ShouldNotBeCalledAdjudicator(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have cough and trouble breathing"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_specialty"] == "Pulmonology"
    assert "Skipped specialty adjudicator" in payload["specialty_reason"]


def test_specialty_adjudicator_still_runs_on_respiratory_cardiac_conflict(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ConflictedReasoner:
        def reason(self, *args, **kwargs) -> StructuredReasoningOutput:
            return StructuredReasoningOutput(
                urgency_level="medium",
                clinical_summary="Chest tightness with wheezing fits a lung problem.",
                patient_friendly_explanation="This may be related to breathing tubes.",
                possible_conditions=[
                    ReasonerCondition(
                        name="Asthma exacerbation",
                        explanation="Wheezing and chest tightness can fit asthma.",
                    )
                ],
                recommended_specialty="Cardiology",
                recommended_actions=["Arrange medical review."],
                red_flags=[],
                clinical_features=ClinicalFeatures(
                    chief_complaint="breathing difficulty",
                    symptoms=["chest discomfort", "breathing difficulty"],
                    body_systems=["cardiac", "respiratory"],
                    red_flags_present=[],
                ),
            )

    class PulmonologyAdjudicator:
        def adjudicate(self, **kwargs):
            return type(
                "Adjudication",
                (),
                {
                    "final_specialty": "Pulmonology",
                    "confidence": 0.9,
                    "reasoning": "Respiratory symptoms dominate.",
                    "relevant_reference_titles": [],
                },
            )()

    monkeypatch.setattr(
        "app.services.triage_service.get_reasoner",
        lambda: ConflictedReasoner(),
    )
    monkeypatch.setattr(
        "app.services.triage_service.get_specialty_adjudicator",
        lambda: PulmonologyAdjudicator(),
    )

    response = client.post(
        "/api/v1/triage",
        json={"query": "I have chest tightness with wheezing"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommended_specialty"] == "Pulmonology"
    assert payload["specialty_reason"] == "Respiratory symptoms dominate."
