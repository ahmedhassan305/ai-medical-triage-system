from app.schemas.triage import ClinicalFeatures
from app.services.clinical_feature_extractor import (
    OllamaClinicalFeatureExtractor,
    _parse_feature_payload,
)
from app.services.clinical_features import (
    assess_urgency_from_features,
    extract_clinical_features,
)


def test_extract_clinical_features_normalizes_patient_language() -> None:
    features = extract_clinical_features(
        "I cannot catch my breath and my chest feels tight since last night."
    )

    assert "breathing difficulty" in features.symptoms
    assert "chest discomfort" in features.symptoms
    assert "respiratory" in features.body_systems
    assert features.duration == "since last night"


def test_feature_based_urgency_uses_combined_findings() -> None:
    features = extract_clinical_features(
        "I have sudden headache with numbness and weakness."
    )

    assert assess_urgency_from_features(features) == "high"


def test_negated_weakness_and_numbness_do_not_create_neurologic_back_case() -> None:
    features = extract_clinical_features(
        "I have back pain after exercise with no numbness and no weakness."
    )

    assert "back pain" in features.symptoms
    assert "numbness" not in features.symptoms
    assert "weakness" not in features.symptoms
    assert "musculoskeletal" in features.body_systems
    assert "neurologic" not in features.body_systems
    assert assess_urgency_from_features(features) == "low"


def test_llm_feature_payload_parser_normalizes_body_system_aliases() -> None:
    features = _parse_feature_payload(
        '{"chief_complaint":"trouble breathing",'
        '"symptoms":["breathing difficulty"],'
        '"body_systems":["pulmonary", "unknown-system"],'
        '"onset":"recent",'
        '"duration":null,'
        '"severity":"moderate",'
        '"progression":"unknown",'
        '"red_flags_present":[],'
        '"red_flags_denied":["chest pain"],'
        '"risk_factors":[],'
        '"missing_critical_details":["how severe the breathing trouble is"]}'
    )

    assert features is not None
    assert features.body_systems == ["respiratory"]
    assert features.symptoms == ["breathing difficulty"]
    assert features.red_flags_denied == ["chest pain"]


def test_llm_feature_prompt_instructs_meaning_not_keywords() -> None:
    local = ClinicalFeatures(symptoms=["abdominal pain"], body_systems=["gastrointestinal"])
    prompt = OllamaClinicalFeatureExtractor(model="test-model")._build_prompt(
        query="my tummy feels twisted",
        local_features=local,
        patient_context=None,
    )

    assert "Extract features from meaning, not exact keyword matching" in prompt
    assert "Do not diagnose and do not choose a specialty" in prompt
    assert "Local rule-based safety extraction" in prompt
    assert "Never copy its values" in prompt
    assert "If duration is not stated, set duration to null" in prompt
    assert "If chest pain is not mentioned" in prompt
    assert "2 days" not in prompt
    assert '"red_flags_denied": []' in prompt
