from __future__ import annotations

from app.schemas.triage import TriageLevel, TriageRequest, TriageResponse

HIGH_RISK_KEYWORDS = [
    "chest pain",
    "shortness of breath",
    "difficulty breathing",
    "stroke",
    "seizure",
    "unconscious",
    "severe bleeding",
    "overdose",
    "suicidal",
]

MEDIUM_RISK_KEYWORDS = [
    "fever",
    "vomiting",
    "dehydration",
    "fracture",
    "burn",
    "infection",
    "migraine",
]


def _match_any(query: str, keywords: list[str]) -> bool:
    q = query.lower()
    return any(k in q for k in keywords)


def run_triage(payload: TriageRequest) -> TriageResponse:
    level: TriageLevel = "low"

    if _match_any(payload.query, HIGH_RISK_KEYWORDS):
        level = "high"
    elif _match_any(payload.query, MEDIUM_RISK_KEYWORDS):
        level = "medium"

    if level == "high":
        actions = [
            "Seek emergency care now.",
            "Call local emergency services if symptoms are severe or worsening.",
        ]
    elif level == "medium":
        actions = [
            "Consider urgent care or a same-day clinic visit.",
            "Seek care sooner if symptoms worsen or new symptoms appear.",
        ]
    else:
        actions = [
            "Consider rest, hydration, and over-the-counter options if appropriate.",
            "Seek care if symptoms persist, worsen, or you are concerned.",
        ]

    return TriageResponse(
        triage_level=level,
        summary="Stub triage result based on keyword matching.",
        actions=actions,
        disclaimer="This is not medical advice. If you think you may have a medical emergency, seek immediate care.",
    )
