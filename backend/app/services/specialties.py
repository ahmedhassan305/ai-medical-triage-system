from __future__ import annotations

import re

TRIAGE_SPECIALTIES: tuple[str, ...] = (
    "Cardiology",
    "Neurology",
    "Neurosurgery",
    "Internal Medicine",
    "Gastroenterology",
    "Dermatology",
    "Psychiatry",
    "Ophthalmology",
    "Orthopedics",
    "ENT",
    "Pediatrics",
    "Family Medicine",
    "Pulmonology",
)

TRIAGE_SPECIALTY_SET = frozenset(TRIAGE_SPECIALTIES)

SPECIALTY_ALIASES: dict[str, str] = {
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "cardiac": "Cardiology",
    "heart": "Cardiology",
    "neurologist": "Neurology",
    "neurology": "Neurology",
    "brain": "Neurology",
    "neurosurgeon": "Neurosurgery",
    "neurosurgery": "Neurosurgery",
    "internist": "Internal Medicine",
    "internal medicine": "Internal Medicine",
    "general medicine": "Internal Medicine",
    "gastroenterologist": "Gastroenterology",
    "gastroenterology": "Gastroenterology",
    "digestive": "Gastroenterology",
    "stomach doctor": "Gastroenterology",
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
    "skin doctor": "Dermatology",
    "psychiatrist": "Psychiatry",
    "psychiatry": "Psychiatry",
    "mental health": "Psychiatry",
    "ophthalmologist": "Ophthalmology",
    "ophthalmology": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "orthopedist": "Orthopedics",
    "orthopedics": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopaedic": "Orthopedics",
    "otolaryngology": "ENT",
    "otolaryngologist": "ENT",
    "ear nose throat": "ENT",
    "ear, nose and throat": "ENT",
    "ent": "ENT",
    "pediatrician": "Pediatrics",
    "pediatrics": "Pediatrics",
    "paediatrics": "Pediatrics",
    "children doctor": "Pediatrics",
    "family medicine": "Family Medicine",
    "family doctor": "Family Medicine",
    "general practice": "Family Medicine",
    "primary care": "Family Medicine",
    "pulmonologist": "Pulmonology",
    "pulmonology": "Pulmonology",
    "pulmonary": "Pulmonology",
    "respiratory": "Pulmonology",
    "lung doctor": "Pulmonology",
}


def canonicalize_specialty(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if not cleaned:
        return None

    if cleaned in TRIAGE_SPECIALTY_SET:
        return cleaned

    lowered = cleaned.lower()
    if lowered in SPECIALTY_ALIASES:
        return SPECIALTY_ALIASES[lowered]

    for alias, specialty in SPECIALTY_ALIASES.items():
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, lowered):
            return specialty

    return None


def allowed_specialties_prompt() -> str:
    return ", ".join(TRIAGE_SPECIALTIES)
