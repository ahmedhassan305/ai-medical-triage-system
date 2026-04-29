from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import DoctorProfile
from app.services.clinical_records import assign_department_to_doctor

SPECIALTY_NORMALIZATION = {
    "cardiologist": "Cardiology",
    "cardiology": "Cardiology",
    "internist": "Internal Medicine",
    "internal medicine": "Internal Medicine",
    "gastroenterologist": "Gastroenterology",
    "gastroenterology": "Gastroenterology",
    "pulmonologist": "Pulmonology",
    "pulmonology": "Pulmonology",
    "orthopedist": "Orthopedics",
    "orthopedics": "Orthopedics",
    "neurologist": "Neurology",
    "neurology": "Neurology",
    "psychiatrist": "Psychiatry",
    "psychiatry": "Psychiatry",
    "neurosurgeon": "Neurosurgery",
    "neurosurgery": "Neurosurgery",
    "dermatologist": "Dermatology",
    "dermatology": "Dermatology",
}

LEGACY_PROTOTYPE_NAMES = {
    "Dr. John Smith",
    "Dr. Sarah Johnson",
    "Dr. Ahmed Hassan",
    "Dr. Maria Garcia",
    "Dr. Michael Chen",
    "Dr. Lisa Anderson",
    "Dr. James Wilson",
    "Dr. Emma Thompson",
    "Dr. Robert Brown",
    "Dr. Patricia Davis",
    "Dr. David Martinez",
    "Dr. Jennifer Lee",
}

LEGACY_FAKE_SOURCE_NAMES = {
    "Egyptian Medical Syndicate Registry",
}


@dataclass(frozen=True)
class DoctorSeedRecord:
    full_name: str
    specialty: str
    clinic: str
    area: str | None
    city: str | None
    source_name: str
    source_url: str
    booking_url: str | None


@dataclass(frozen=True)
class DoctorImportResult:
    inserted: int
    updated: int
    removed_legacy: int
    total_seed_records: int


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _truncate(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    return value[:max_length].strip()


def normalize_specialty(value: str) -> str:
    normalized = value.strip().lower()
    mapped = SPECIALTY_NORMALIZATION.get(normalized)
    if mapped:
        return mapped
    return value.strip()


def normalize_seed_record(record: dict[str, Any]) -> DoctorSeedRecord:
    full_name = str(record.get("full_name", "")).strip()
    if not full_name:
        raise ValueError("Doctor seed record requires full_name.")
    if full_name.lower().startswith("doctor "):
        full_name = full_name[7:].strip()
    full_name = _truncate(full_name, 200) or ""

    specialty = normalize_specialty(str(record.get("specialty", "")).strip())
    specialty = _truncate(specialty, 120) or ""
    if not specialty:
        raise ValueError(f"Doctor seed record for {full_name} requires specialty.")

    clinic = _truncate(str(record.get("clinic", "")).strip(), 200) or ""
    if not clinic:
        raise ValueError(f"Doctor seed record for {full_name} requires clinic.")

    source_name = _truncate(str(record.get("source_name", "")).strip(), 120) or ""
    source_url = _truncate(str(record.get("source_url", "")).strip(), 500) or ""
    if not source_name or not source_url:
        raise ValueError(
            f"Doctor seed record for {full_name} requires source_name and source_url."
        )

    booking_url = _truncate(_normalize_optional_text(record.get("booking_url")), 500)
    return DoctorSeedRecord(
        full_name=full_name,
        specialty=specialty,
        clinic=clinic,
        area=_truncate(_normalize_optional_text(record.get("area")), 120),
        city=_truncate(_normalize_optional_text(record.get("city")), 120),
        source_name=source_name,
        source_url=source_url,
        booking_url=booking_url,
    )


def load_seed_records(seed_path: str | Path) -> list[DoctorSeedRecord]:
    payload = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        raw_records = payload.get("doctors", [])
    elif isinstance(payload, list):
        raw_records = payload
    else:
        raise ValueError(
            "Doctor seed file must contain either a list or a doctors map."
        )

    if not isinstance(raw_records, list):
        raise ValueError("Doctor seed file doctors entry must be a list.")

    return [normalize_seed_record(record) for record in raw_records]


def cleanup_legacy_seed_data(db: Session) -> int:
    removed = 0

    prototype_matches = (
        db.query(DoctorProfile)
        .filter(DoctorProfile.full_name.in_(sorted(LEGACY_PROTOTYPE_NAMES)))
        .all()
    )
    for doctor in prototype_matches:
        db.delete(doctor)
        removed += 1

    fake_source_matches = (
        db.query(DoctorProfile)
        .filter(
            or_(
                DoctorProfile.source_name.in_(sorted(LEGACY_FAKE_SOURCE_NAMES)),
                DoctorProfile.source_url == "https://doctors.example.com/registry",
            )
        )
        .all()
    )
    for doctor in fake_source_matches:
        db.delete(doctor)
        removed += 1

    return removed


def import_seed_records(
    db: Session,
    records: list[DoctorSeedRecord],
    *,
    clean_legacy: bool = True,
) -> DoctorImportResult:
    inserted = 0
    updated = 0
    removed_legacy = cleanup_legacy_seed_data(db) if clean_legacy else 0

    for record in records:
        existing = (
            db.query(DoctorProfile)
            .filter(
                or_(
                    DoctorProfile.source_url == record.source_url,
                    (
                        (DoctorProfile.full_name == record.full_name)
                        & (DoctorProfile.specialty == record.specialty)
                    ),
                )
            )
            .first()
        )

        if existing is None:
            existing = DoctorProfile(
                full_name=record.full_name,
                specialty=record.specialty,
                clinic=record.clinic,
                area=record.area,
                city=record.city,
                source_name=record.source_name,
                source_url=record.source_url,
                booking_url=record.booking_url,
            )
            db.add(existing)
            db.flush()
            assign_department_to_doctor(db, existing, department_name=record.specialty)
            inserted += 1
            continue

        existing.full_name = record.full_name
        existing.specialty = record.specialty
        existing.clinic = record.clinic
        existing.area = record.area
        existing.city = record.city
        existing.source_name = record.source_name
        existing.source_url = record.source_url
        existing.booking_url = record.booking_url
        assign_department_to_doctor(db, existing, department_name=record.specialty)
        updated += 1

    db.commit()
    return DoctorImportResult(
        inserted=inserted,
        updated=updated,
        removed_legacy=removed_legacy,
        total_seed_records=len(records),
    )
