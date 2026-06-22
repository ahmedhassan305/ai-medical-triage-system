from __future__ import annotations

import re
from collections.abc import Iterable

from app.schemas.triage import ClinicalFeatures, TriageLevel

_BODY_SYSTEM_PATTERNS: dict[str, tuple[str, ...]] = {
    # Keep cardiac matching specific. Generic "chest" wording is common in
    # lung problems too, so specialty routing should not treat it as cardiac
    # unless there is a heart-pattern phrase or cardiac symptom.
    "cardiac": (
        "heart",
        "myocardial infarction",
        "hypertension crisis",
        "hypertensive crisis",
        "hypertensive emergency",
        "palpitation",
        "chest pressure",
        "crushing chest",
        "elephant on chest",
        "chest is killing me",
        "chest killing me",
        "pain spreading to jaw",
        "pain spreading to arm",
        "chest pain and left arm",
        "chest hurts and left arm",
    ),
    "respiratory": (
        "breath",
        "wheez",
        "cough",
        "lung",
        "pneumonia",
        "asthma",
        "asthma exacerbation",
        "stridor",
        "hemoptysis",
        "coughing up blood",
        "respiratory distress",
        "dyspnea",
    ),
    "neurologic": (
        "headache",
        "migraine",
        "seizure",
        "stroke",
        "numb",
        "tingl",
        "weakness",
        "confus",
        "altered mental status",
        "facial droop",
        "face drooping",
        "drooping",
        "slurred speech",
        "can't talk",
        "cant talk",
        "vision change",
        "flashing lights",
        "paresthesia",
        "room is spinning",
        "pins and needles",
        "neuropathy",
    ),
    "gastrointestinal": (
        "abdominal",
        "stomach",
        "belly",
        "ascites",
        "abdominal swelling",
        "swollen abdomen",
        "jaundice",
        "yellow eyes",
        "yellow skin",
        "dark urine",
        "liver",
        "hepatic",
        "vomit",
        "nausea",
        "diarrhea",
        "constipation",
        "bowel",
        "stool",
        "poop",
        "defecat",
        "straining",
        "strain during bowel",
        "hard stool",
        "rectal",
        "anal",
        "anus",
        "reflux",
        "right lower quadrant",
        "right upper quadrant",
        "epigastric",
        "pancreatitis",
        "cholecystitis",
        "appendicitis",
    ),
    "genitourinary": (
        "urinary",
        "dysuria",
        "frequency",
        "pee",
        "urine",
        "flank",
        "hematuria",
        "kidney stone",
        "nephrolithiasis",
    ),
    "musculoskeletal": (
        "back",
        "lower back",
        "buttock",
        "gluteal",
        "neck",
        "joint",
        "knee",
        "ankle",
        "wrist",
        "fracture",
        "broken",
        "sprain",
        "strain",
    ),
    "skin": ("rash", "itch", "hives", "blister", "skin", "burn", "red skin"),
    "mental_health": (
        "anxious",
        "anxiety",
        "panic",
        "freaking out",
        "worried",
        "stressed",
        "depress",
        "nothing makes me happy",
        "anhedonia",
        "insomnia",
        "suicidal",
        "hopeless",
    ),
    "ent": (
        "ear",
        "throat",
        "sinus",
        "hearing",
        "swallow",
        "runny nose",
        "sore throat",
        "congested",
        "nasal congestion",
        "face hurts",
    ),
    "eye": ("eye", "vision", "blurred", "double vision"),
    "general": ("fever", "fatigue", "chills", "tired", "infection"),
}

_NORMALIZED_SYMPTOMS: dict[str, tuple[str, ...]] = {
    "chest discomfort": (
        "chest pain",
        "myocardial infarction",
        "chest pressure",
        "chest tightness",
        "chest feels tight",
        "tight chest",
        "crushing chest",
        "chest is killing me",
        "chest killing me",
        "my chest hurts",
    ),
    "breathing difficulty": (
        "shortness of breath",
        "short of breath",
        "difficulty breathing",
        "trouble breathing",
        "can't breathe",
        "cannot breathe",
        "cannot catch my breath",
        "can't catch my breath",
        "cant catch my breath",
        "respiratory distress",
        "rapid breathing",
        "dyspnea",
        "stridor",
    ),
    "wheezing": ("wheezing", "wheeze", "whistling sound"),
    "pneumonia concern": ("pneumonia",),
    "cough": (
        "cough",
        "coughing",
        "dry cough",
        "productive cough",
        "barky cough",
    ),
    "fever": ("fever", "temperature", "burning up"),
    "vomiting": ("vomiting", "throwing up", "can't keep food down"),
    "diarrhea": ("diarrhea", "loose stool"),
    "constipation": (
        "constipation",
        "constipated",
        "hard stool",
        "hard stools",
        "poop too hard",
        "straining",
        "strain during bowel",
        "straining during bowel",
    ),
    "painful bowel movement": (
        "pain when i poop",
        "pain when pooping",
        "pain while pooping",
        "pain after pooping",
        "poop too hard i feel pain",
        "when i poop too hard i feel pain",
        "pain with bowel movement",
        "painful bowel movement",
        "pain during bowel movement",
        "pain when passing stool",
        "pain while passing stool",
        "pain after passing stool",
        "rectal pain",
        "anal pain",
        "anus pain",
    ),
    "headache": ("headache", "head pain", "head is killing me"),
    "dizziness": ("dizzy", "dizziness", "lightheaded", "room spinning"),
    "numbness": ("numbness", "numb", "pins and needles", "tingling"),
    "weakness": ("weakness", "weak", "paralysis"),
    "rash": ("rash", "hives", "itching", "itchy", "blistering"),
    "nasal congestion": ("runny nose", "congested", "nasal congestion"),
    "sore throat": ("sore throat", "throat is really sore", "hurts to swallow"),
    "ear pain": ("ear pain", "ear hurts"),
    "anxiety": ("anxiety", "freaking out", "worried", "stressed"),
    "low mood": ("nothing makes me happy", "depress", "anhedonia"),
    "insomnia": ("insomnia", "can't sleep", "cant sleep"),
    "abdominal pain": (
        "abdominal pain",
        "stomach pain",
        "belly pain",
        "tummy pain",
        "cramps",
        "right lower quadrant pain",
        "right upper quadrant pain",
        "epigastric pain",
        "flank pain",
        "right side hurts",
        "side hurts",
    ),
    "urinary symptoms": (
        "dysuria",
        "frequency",
        "burns when i pee",
        "burning when i pee",
        "gotta go all the time",
        "hematuria",
        "pee is red",
        "red urine",
    ),
    "reduced urination": (
        "hasnt had a wet diaper",
        "hasn't had a wet diaper",
        "no wet diaper",
        "not peeing",
        "not urinating",
    ),
    "abdominal swelling": (
        "abdominal swelling",
        "swollen abdomen",
        "belly swelling",
        "ascites",
        "fluid in my belly",
    ),
    "jaundice": (
        "jaundice",
        "yellow eyes",
        "yellow skin",
        "yellowing of skin",
        "yellowing of eyes",
    ),
    "dark urine": ("dark urine", "tea colored urine", "brown urine"),
    "fatigue": ("fatigue", "tired", "lack of energy", "exhausted"),
    "back pain": (
        "back pain",
        "backache",
        "lower back",
        "lower back pain",
        "right lower back",
        "above my ass",
        "above my butt",
        "above my buttock",
        "above the buttock",
        "gluteal pain",
    ),
    "neck pain": ("neck pain", "neck hurts"),
    "joint pain": ("joint pain", "knee pain", "ankle pain", "shoulder pain"),
    "fracture concern": ("fracture", "broken arm", "arm is broken", "broken bone"),
    "palpitations": ("heart racing", "heart pounding", "palpitations", "flutter"),
    "altered mental status": (
        "altered mental status",
        "confusion",
        "confused",
        "not acting right",
    ),
    "drooling": ("drooling",),
    "trouble swallowing": ("dysphagia", "trouble swallowing", "can't swallow"),
}

_RED_FLAG_PATTERNS: dict[str, tuple[str, ...]] = {
    "breathing distress": (
        "can't breathe",
        "cannot breathe",
        "not breathing",
        "severe shortness of breath",
        "severe trouble breathing",
        "severe difficulty breathing",
        "respiratory distress",
        "rapid breathing",
        "blue lips",
        "blue fingertips",
        "barely speak",
        "cant catch my breath",
        "can't catch my breath",
    ),
    "possible heart emergency": (
        "chest pain with shortness of breath",
        "chest pain and shortness of breath",
        "chest pressure with sweating",
        "crushing chest pain",
        "chest is killing me",
        "chest killing me",
        "chest pain and left arm",
        "chest pain with left arm",
        "chest hurts and left arm",
        "myocardial infarction",
        "radiating to left arm",
        "radiating to the left arm",
        "pain spreading to jaw",
        "pain spreading to arm",
        "heart attack",
        "hypertension crisis",
        "hypertensive crisis",
        "hypertensive emergency",
    ),
    "stroke-like symptoms": (
        "face drooping",
        "slurred speech",
        "trouble speaking",
        "one-sided weakness",
        "stroke",
        "face is drooping",
        "cant talk right",
        "can't talk right",
        "arm is weak",
    ),
    "seizure or loss of consciousness": (
        "seizure",
        "passed out",
        "passing out",
        "fainted",
        "unconscious",
        "unresponsive",
    ),
    "major bleeding": (
        "severe bleeding",
        "won't stop bleeding",
        "bleeding a lot",
        "coughing up blood",
        "hemoptysis",
    ),
    "self-harm risk": (
        "suicidal",
        "want to hurt myself",
    ),
    "possible serious allergy": (
        "throat closing",
        "tongue swelling",
        "can't swallow",
    ),
    "possible spinal nerve emergency": (
        "back pain with numbness",
        "back pain with weakness",
    ),
    "loss of bladder or bowel control": (
        "loss of bladder control",
        "loss of bowel control",
        "incontinence",
    ),
    "possible serious liver disease": (
        "vomiting blood",
        "black stool",
        "black stools",
        "confusion with jaundice",
        "jaundice with confusion",
    ),
    "possible meningitis": (
        "headache with stiff neck",
        "stiff neck and high fever",
        "neck is super stiff",
        "fever and stiff neck",
    ),
    "possible abdominal surgical emergency": (
        "appendicitis",
        "right lower quadrant pain and fever",
        "right side hurts really bad",
        "belly hurts really bad on the right side",
        "right side and im running a fever",
        "right side and i'm running a fever",
        "cholecystitis",
        "right upper quadrant pain",
        "right side hurts really bad after i ate greasy food",
        "severe epigastric pain",
        "pancreatitis",
    ),
    "possible dehydration": (
        "hasnt had a wet diaper",
        "hasn't had a wet diaper",
        "no wet diaper",
        "throwing up everything",
        "can't keep food down",
    ),
    "possible toxic ingestion": (
        "overdose",
        "opioid overdose",
    ),
    "major burn": (
        "thermal burns",
        "covering 30% of body surface",
        "severe burn",
    ),
    "possible sepsis": (
        "sepsis",
        "hypotension",
        "altered mental status",
    ),
    "severe asthma flare": (
        "acute asthma exacerbation",
        "asthma exacerbation",
        "asthma attack",
    ),
}


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _extract_symptoms(lowered: str) -> list[str]:
    symptoms: list[str] = []
    for normalized, variants in _NORMALIZED_SYMPTOMS.items():
        if _contains_any(lowered, variants):
            symptoms.append(normalized)
    return symptoms


def _extract_body_systems(lowered: str) -> list[str]:
    body_systems = [
        system
        for system, patterns in _BODY_SYSTEM_PATTERNS.items()
        if _contains_any(lowered, patterns)
    ]
    return body_systems or ["general"]


def _extract_onset(lowered: str) -> str:
    if _contains_any(
        lowered,
        (
            "sudden",
            "suddenly",
            "all of a sudden",
            "right now",
            "started today",
            "just started",
        ),
    ):
        return "sudden"
    if _contains_any(lowered, ("for weeks", "for months", "long time", "chronic")):
        return "longstanding"
    if _contains_any(
        lowered,
        (
            "few days",
            "several days",
            "since yesterday",
            "this morning",
            "since this morning",
        ),
    ):
        return "recent"
    return "unknown"


def _extract_duration(lowered: str) -> str | None:
    match = re.search(
        r"\b(\d+\s*(?:minutes?|hours?|days?|weeks?|months?))\b",
        lowered,
    )
    if match:
        return match.group(1)
    if "since yesterday" in lowered:
        return "since yesterday"
    if "since this morning" in lowered or "this morning" in lowered:
        return "since this morning"
    if "last night" in lowered:
        return "since last night"
    return None


def _extract_severity(lowered: str) -> str:
    if _contains_any(
        lowered,
        (
            "severe",
            "worst",
            "can't function",
            "can barely",
            "very bad",
            "really bad",
            "unbearable",
            "killing me",
        ),
    ):
        return "severe"
    if _contains_any(lowered, ("mild", "slight", "a little")):
        return "mild"
    if _contains_any(lowered, ("moderate", "noticeable")):
        return "moderate"
    return "unknown"


def _extract_progression(lowered: str) -> str:
    if _contains_any(lowered, ("worse", "worsening", "getting worse")):
        return "worsening"
    if _contains_any(lowered, ("improving", "getting better", "better now")):
        return "improving"
    return "unknown"


def _extract_red_flags(lowered: str) -> list[str]:
    return [
        label
        for label, patterns in _RED_FLAG_PATTERNS.items()
        if _contains_any(lowered, patterns)
    ]


def _extract_negated_red_flags(lowered: str) -> list[str]:
    negated: list[str] = []
    simple_negations = {
        "breathing difficulty": ("no shortness of breath", "no trouble breathing"),
        "chest pain": ("no chest pain",),
        "vomiting": ("no vomiting", "not vomiting"),
        "fever": ("no fever",),
        "weakness": ("no weakness",),
        "numbness": ("no numbness",),
    }
    for label, patterns in simple_negations.items():
        if _contains_any(lowered, patterns):
            negated.append(label)
    return negated


def _missing_details(symptoms: list[str], onset: str, severity: str) -> list[str]:
    missing: list[str] = []
    if onset == "unknown":
        missing.append("when it started")
    if severity == "unknown":
        missing.append("how severe it is")
    if "chest discomfort" in symptoms:
        missing.extend(["whether it spreads", "whether activity makes it worse"])
    if "headache" in symptoms:
        missing.append("whether it started suddenly")
    if "abdominal pain" in symptoms:
        missing.append("where the pain is strongest")
    if "back pain" in symptoms or "neck pain" in symptoms:
        missing.append("whether there is weakness or numbness")
    return list(dict.fromkeys(missing))


def extract_clinical_features(
    query: str,
    *,
    age: int | None = None,
) -> ClinicalFeatures:
    lowered = query.lower()
    symptoms = _extract_symptoms(lowered)
    onset = _extract_onset(lowered)
    severity = _extract_severity(lowered)
    body_systems = _extract_body_systems(lowered)
    red_flags = _extract_red_flags(lowered)
    denied_features = _extract_negated_red_flags(lowered)
    if denied_features:
        symptoms = [symptom for symptom in symptoms if symptom not in denied_features]
        if "neurologic" in body_systems and not {
            "headache",
            "dizziness",
            "numbness",
            "weakness",
        }.intersection(symptoms):
            body_systems = [
                system for system in body_systems if system != "neurologic"
            ] or ["general"]

    risk_factors: list[str] = []
    if age is not None and age < 5:
        risk_factors.append("young child")
    if age is not None and age >= 65:
        risk_factors.append("older adult")

    return ClinicalFeatures(
        chief_complaint=symptoms[0] if symptoms else None,
        symptoms=symptoms,
        body_systems=body_systems,
        onset=onset,
        duration=_extract_duration(lowered),
        severity=severity,
        progression=_extract_progression(lowered),
        red_flags_present=red_flags,
        red_flags_denied=denied_features,
        risk_factors=risk_factors,
        missing_critical_details=_missing_details(symptoms, onset, severity),
    )


def merge_clinical_features(
    base: ClinicalFeatures,
    extracted: ClinicalFeatures | None,
) -> ClinicalFeatures:
    if extracted is None:
        return base

    return ClinicalFeatures(
        chief_complaint=extracted.chief_complaint or base.chief_complaint,
        symptoms=list(dict.fromkeys([*base.symptoms, *extracted.symptoms])),
        body_systems=list(dict.fromkeys([*base.body_systems, *extracted.body_systems])),
        onset=extracted.onset if extracted.onset != "unknown" else base.onset,
        duration=extracted.duration or base.duration,
        severity=(
            extracted.severity if extracted.severity != "unknown" else base.severity
        ),
        progression=(
            extracted.progression
            if extracted.progression != "unknown"
            else base.progression
        ),
        red_flags_present=list(
            dict.fromkeys([*base.red_flags_present, *extracted.red_flags_present])
        ),
        red_flags_denied=list(
            dict.fromkeys([*base.red_flags_denied, *extracted.red_flags_denied])
        ),
        risk_factors=list(dict.fromkeys([*base.risk_factors, *extracted.risk_factors])),
        missing_critical_details=list(
            dict.fromkeys(
                [*base.missing_critical_details, *extracted.missing_critical_details]
            )
        ),
    )


def assess_urgency_from_features(
    features: ClinicalFeatures,
    *,
    age: int | None = None,
) -> TriageLevel:
    symptoms = set(features.symptoms)
    systems = set(features.body_systems)
    red_flags = set(features.red_flags_present)

    if red_flags.intersection(
        {
            "breathing distress",
            "possible heart emergency",
            "stroke-like symptoms",
            "seizure or loss of consciousness",
            "major bleeding",
            "self-harm risk",
            "possible serious allergy",
            "possible serious liver disease",
            "possible meningitis",
            "possible abdominal surgical emergency",
            "possible toxic ingestion",
            "major burn",
            "possible sepsis",
            "severe asthma flare",
        }
    ):
        return "high"

    if "possible spinal nerve emergency" in red_flags:
        if "loss of bladder or bowel control" in red_flags:
            return "high"
        return "medium"

    if age is not None and age <= 5:
        if {
            "fever",
            "vomiting",
            "reduced urination",
            "breathing difficulty",
        }.intersection(symptoms) or {
            "possible dehydration",
            "breathing distress",
        }.intersection(
            red_flags
        ):
            return "high"
        if {"fever", "cough"}.issubset(symptoms) and "respiratory" in systems:
            return "high"

    if age is not None and age < 13:
        if {"breathing distress", "possible dehydration"}.intersection(red_flags):
            return "high"
        if "wheezing" in symptoms and "respiratory" in systems:
            return "high"

    if age is not None and age >= 65:
        if {"dizziness", "weakness"}.intersection(symptoms):
            return "medium"
        if {"pneumonia concern", "breathing difficulty"}.intersection(symptoms) and {
            "fever",
            "cough",
        }.intersection(symptoms):
            return "high"

    if (
        "chest discomfort" in symptoms
        and "breathing difficulty" in symptoms
        and "cardiac" in systems
    ):
        return "high"

    if (
        "chest discomfort" in symptoms
        and "possible heart emergency" in red_flags
        and "cardiac" in systems
    ):
        return "high"

    if "breathing difficulty" in symptoms and (
        "chest discomfort" in symptoms
        or "wheezing" in symptoms
        or "respiratory" in systems
    ):
        if features.severity == "severe":
            return "high"
        return "medium"

    if (
        "headache" in symptoms
        and features.onset == "sudden"
        and {"weakness", "numbness"}.intersection(symptoms)
    ):
        return "high"

    if "back pain" in symptoms and {"weakness", "numbness"}.intersection(symptoms):
        return "medium"

    if {"fever", "vomiting"}.intersection(symptoms):
        return "medium"

    if {"abdominal pain", "urinary symptoms"}.intersection(symptoms) and (
        "genitourinary" in systems
    ):
        return "medium"

    if "fracture concern" in symptoms:
        return "medium"

    if "jaundice" in symptoms and {
        "abdominal swelling",
        "dark urine",
    }.intersection(symptoms):
        return "high"

    if "jaundice" in symptoms:
        return "medium"

    if "abdominal pain" in symptoms and features.severity == "severe":
        return "medium"

    if features.severity == "severe" and features.progression == "worsening":
        return "medium"

    return "low"
