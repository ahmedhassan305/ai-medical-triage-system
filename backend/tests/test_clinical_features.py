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
