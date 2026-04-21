from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, DoctorProfile
from app.services.doctor_seed_importer import (
    import_seed_records,
    load_seed_records,
    normalize_seed_record,
)


def _create_memory_session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_normalize_seed_record_maps_specialty_and_name() -> None:
    record = normalize_seed_record(
        {
            "full_name": "Doctor Waleed Etman",
            "specialty": "Cardiologist",
            "clinic": "Consultant Cardiologist",
            "area": "Glym",
            "city": "Alexandria",
            "source_name": "Vezeeta public directory",
            "source_url": "https://example.com/waleed",
            "booking_url": "https://example.com/waleed",
        }
    )

    assert record.full_name == "Waleed Etman"
    assert record.specialty == "Cardiology"
    assert record.area == "Glym"
    assert record.city == "Alexandria"


def test_load_seed_records_reads_curated_json(tmp_path: Path) -> None:
    seed_path = tmp_path / "seed.json"
    seed_path.write_text(
        json.dumps(
            {
                "doctors": [
                    {
                        "full_name": "Rasha Daabis",
                        "specialty": "Pulmonologist",
                        "clinic": "Professor of Pulmonology",
                        "area": "Smouha",
                        "city": "Alexandria",
                        "source_name": "Vezeeta public directory",
                        "source_url": "https://example.com/rasha",
                        "booking_url": "https://example.com/rasha",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    records = load_seed_records(seed_path)
    assert len(records) == 1
    assert records[0].specialty == "Pulmonology"


def test_import_seed_records_upserts_and_cleans_legacy_data() -> None:
    db = _create_memory_session()
    public_label = (
        "Lecturer of Internal Medicine, Faculty of Medicine Alexandria University"
    )
    db.add(
        DoctorProfile(
            full_name="Dr. John Smith",
            specialty="Cardiology",
            clinic="Legacy Fake Clinic",
        )
    )
    db.add(
        DoctorProfile(
            full_name="Placeholder Registry Doctor",
            specialty="Pulmonology",
            clinic="Legacy Registry Clinic",
            source_name="Egyptian Medical Syndicate Registry",
            source_url="https://doctors.example.com/registry",
        )
    )
    db.commit()

    records = [
        normalize_seed_record(
            {
                "full_name": "Hussein Saad",
                "specialty": "Internist",
                "clinic": public_label,
                "area": "El-Mandara",
                "city": "Alexandria",
                "source_name": "Vezeeta public directory",
                "source_url": "https://example.com/hussein",
                "booking_url": "https://example.com/hussein",
            }
        )
    ]

    first_import = import_seed_records(db, records)
    assert first_import.inserted == 1
    assert first_import.updated == 0
    assert first_import.removed_legacy == 2

    seeded = (
        db.query(DoctorProfile).filter(DoctorProfile.full_name == "Hussein Saad").one()
    )
    assert seeded.specialty == "Internal Medicine"
    assert seeded.source_name == "Vezeeta public directory"

    updated_records = [
        normalize_seed_record(
            {
                "full_name": "Hussein Saad",
                "specialty": "Internal Medicine",
                "clinic": "Updated public practice label",
                "area": "El-Mandara",
                "city": "Alexandria",
                "source_name": "Vezeeta public directory",
                "source_url": "https://example.com/hussein",
                "booking_url": "https://example.com/hussein",
            }
        )
    ]
    second_import = import_seed_records(db, updated_records)
    assert second_import.inserted == 0
    assert second_import.updated == 1

    db.refresh(seeded)
    assert seeded.clinic == "Updated public practice label"
    assert db.query(DoctorProfile).count() == 1
