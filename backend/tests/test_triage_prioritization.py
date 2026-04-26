"""
Tests for improved triage clinical prioritization.

These tests validate that the triage system correctly handles:
1. Red-flag symptom combinations (e.g., head trauma + vomiting + severe headache)
2. High-risk evidence from RAG
3. Specialty mapping (not recommending Gastroenterology for head injuries)
4. Condition ranking with context penalties
"""

import pytest
from fastapi.testclient import TestClient

from app.services.triage_service import _assess_red_flags, _collect_condition_scores
from app.rag.retriever import RetrievedChunk
from app.model.reasoner import StructuredReasoningOutput


def test_head_trauma_with_vomiting_and_severe_headache_is_high_urgency(
    client: TestClient,
) -> None:
    """Head injury + severe headache + vomiting should result in HIGH urgency."""
    query = "I hit my head hard in the wall and i feel nauseous and i want to vomit and i have a very painful headache"
    
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["urgency_level"] == "high", (
        f"Expected HIGH urgency for head trauma + vomiting + severe headache, "
        f"got {payload['urgency_level']}"
    )
    assert payload["triage_level"] == "high"
    assert payload["recommended_specialty"] != "Gastroenterology", (
        "Should not recommend Gastroenterology for head trauma scenario"
    )
    
    # Verify red flags are captured
    assert len(payload["red_flags"]) > 0, "Should have red flags for head trauma"
    assert any(
        "head" in flag.lower() or "trauma" in flag.lower()
        for flag in payload["red_flags"]
    ), "Red flags should mention head injury"
    
    # Verify Neurology or related specialty is recommended
    assert payload["recommended_specialty"] in [
        "Neurology",
        "Emergency Medicine",
        "Trauma Surgery",
    ], f"Expected neuro-related specialty, got {payload['recommended_specialty']}"


def test_chest_pain_with_shortness_of_breath_is_high_urgency(
    client: TestClient,
) -> None:
    """Chest pain + shortness of breath should result in HIGH urgency."""
    query = "I have severe chest pain and difficulty breathing"
    
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["urgency_level"] == "high"
    assert payload["recommended_specialty"] in [
        "Cardiology",
        "Pulmonology",
        "Emergency Medicine",
    ], f"Expected cardio/pulmo specialty, got {payload['recommended_specialty']}"


def test_stroke_symptoms_is_high_urgency(client: TestClient) -> None:
    """Stroke-like symptoms should result in HIGH urgency."""
    query = "I suddenly have facial drooping, one-sided weakness, and trouble speaking"
    
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["urgency_level"] == "high"
    assert payload["recommended_specialty"] in ["Neurology", "Emergency Medicine"]


def test_red_flag_assessment_detects_head_trauma_combination():
    """Test the red flag assessment function directly for head trauma."""
    query = "hit my head hard and now have severe headache and vomiting"
    
    assessment = _assess_red_flags(query, None, [])
    
    assert assessment.urgency_floor == "high"
    assert len(assessment.warning_labels) > 0
    assert assessment.specialty_override == "Neurology"
    assert assessment.patient_message is not None
    assert "head" in assessment.patient_message.lower()


def test_context_penalty_prevents_gi_dominance_in_head_trauma():
    """Test that GI conditions are penalized in head trauma context."""
    from app.services.triage_service import _context_penalty, RedFlagAssessment
    
    assessment = RedFlagAssessment(
        urgency_floor="high",
        specialty_override="Neurology",
    )
    
    # GI conditions should be strongly penalized in neurology context
    gastritis_penalty = _context_penalty("Gastritis", assessment)
    gerd_penalty = _context_penalty("GERD", assessment)
    gastroenteritis_penalty = _context_penalty("Gastroenteritis", assessment)
    
    assert gastritis_penalty < 0, "Should penalize Gastritis in neurology context"
    assert gerd_penalty < 0, "Should penalize GERD in neurology context"
    assert gastroenteritis_penalty < 0, "Should penalize Gastroenteritis in neuro context"
    
    # Neurological conditions should not be penalized
    concussion_penalty = _context_penalty("Concussion", assessment)
    hematoma_penalty = _context_penalty("Intracranial Hematoma", assessment)
    
    assert concussion_penalty >= 0, "Should not penalize Concussion in neurology context"
    assert hematoma_penalty >= 0, "Should not penalize Hematoma in neurology context"


def test_head_injury_not_ranked_as_gastroenterology(
    client: TestClient,
) -> None:
    """Verify head injury scenarios don't result in Gastroenterology recommendation."""
    test_queries = [
        "hit my head and feeling nauseous",
        "head injury with vomiting",
        "fell and hit my head, now dizzy and nauseous",
    ]
    
    for query in test_queries:
        response = client.post("/api/v1/triage", json={"query": query})
        assert response.status_code == 200
        
        payload = response.json()
        assert payload["recommended_specialty"] != "Gastroenterology", (
            f"Query '{query}' should not recommend Gastroenterology"
        )


def test_severe_headache_with_trauma_shows_dangerous_conditions():
    """Verify dangerous head-injury conditions are surfaced."""
    query = "hit my head hard and have severe worst-of-my-life headache"
    
    from app.services.triage_service import triage
    from app.db.session import SessionLocal
    
    result = triage(query, patient_id=None, db=None, current_user=None)
    
    # Check that dangerous conditions are in the top results
    condition_names = [c.name.lower() for c in result.suspected_conditions]
    
    # Should include head-injury related conditions
    assert any(
        keyword in " ".join(condition_names)
        for keyword in [
            "concussion",
            "hematoma",
            "traumatic",
            "head injury",
        ]
    ), f"Expected head injury conditions, got: {condition_names}"


def test_emergency_assessment_needed_message_for_high_urgency(
    client: TestClient,
) -> None:
    """Verify high urgency cases show appropriate urgent messaging."""
    query = "I have severe chest pain and can't catch my breath"
    
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["urgency_level"] == "high"
    assert "emergency" in payload["urgency_label"].lower(), (
        f"Expected 'emergency' in urgency label for high urgency, "
        f"got: {payload['urgency_label']}"
    )
    assert "now" in payload["urgency_label"].lower(), (
        "Should convey immediate action needed"
    )


def test_low_risk_query_does_not_escalate_unnecessarily(
    client: TestClient,
) -> None:
    """Verify that low-risk queries don't escalate to HIGH urgency unnecessarily."""
    query = "I have mild seasonal allergies"
    
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    assert payload["urgency_level"] == "low", (
        f"Expected LOW urgency for mild allergies, got {payload['urgency_level']}"
    )


@pytest.mark.parametrize(
    ("query", "should_be_high"),
    [
        ("I hit my head and feel vomiting and severe headache", True),
        ("chest pain and shortness of breath", True),
        ("sudden facial drooping and weakness", True),
        ("severe bleeding that won't stop", True),
        ("throat closing up", True),
        ("mild cough", False),
        ("occasional headache", False),
        ("sore throat", False),
    ],
)
def test_urgency_escalation_matrix(
    client: TestClient, query: str, should_be_high: bool
) -> None:
    """Comprehensive test matrix for urgency escalation."""
    response = client.post("/api/v1/triage", json={"query": query})
    assert response.status_code == 200
    
    payload = response.json()
    is_high = payload["urgency_level"] == "high"
    
    assert is_high == should_be_high, (
        f"Query '{query}': expected urgency high={should_be_high}, "
        f"got {payload['urgency_level']}"
    )
