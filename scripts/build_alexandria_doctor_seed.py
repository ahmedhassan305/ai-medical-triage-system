#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "doctors"
    / "alexandria_public_directory_seed.json"
)
BASE_URL = "https://www.vezeeta.com"
SOURCE_NAME = "Vezeeta public directory"
SPECIALTY_PAGES = {
    "Cardiology": "https://www.vezeeta.com/en/doctor/cardiology/alexandria",
    "Neurology": "https://www.vezeeta.com/en/doctor/neurology/alexandria",
    "Neurosurgery": "https://www.vezeeta.com/en/doctor/neurosurgery/alexandria",
    "Internal Medicine": "https://www.vezeeta.com/en/doctor/internal-medicine/alexandria",
    "Gastroenterology": "https://www.vezeeta.com/en/doctor/adult-gastroenterology-and-endoscopy/alexandria",
    "Dermatology": "https://www.vezeeta.com/en/doctor/dermatology/alexandria",
    "Psychiatry": "https://www.vezeeta.com/en/doctor/psychiatry/alexandria",
    "Ophthalmology": "https://www.vezeeta.com/en/doctor/ophthalmology/alexandria",
    "Orthopedics": "https://www.vezeeta.com/en/doctor/orthopedics/alexandria",
    "ENT": "https://www.vezeeta.com/en/doctor/ear-nose-and-throat/alexandria",
    "Pediatrics": "https://www.vezeeta.com/en/doctor/pediatrics/alexandria",
    "Family Medicine": "https://www.vezeeta.com/en/doctor/family-medicine/alexandria",
}
JSON_LD_PATTERN = re.compile(
    r'<script type="application/ld\+json">(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the canonical Alexandria doctor seed from public "
            "Vezeeta directory pages."
        )
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the canonical doctor seed JSON.",
    )
    return parser.parse_args()


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    normalized = normalized.replace('\\"', '"').replace("\\'", "'")
    normalized = normalized.strip(" '\"")
    return normalized or None


def _extract_physicians(html: str) -> list[dict[str, Any]]:
    physicians: list[dict[str, Any]] = []
    for block in JSON_LD_PATTERN.findall(html):
        try:
            parsed = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("@type") == "Physician":
            physicians.append(parsed)
    return physicians


def _doctor_entry(physician: dict[str, Any], specialty: str) -> dict[str, str | None]:
    name = _normalize_text(physician.get("name"))
    if not name:
        raise ValueError("Physician entry missing name.")

    profile_url = _normalize_text(physician.get("url"))
    if not profile_url:
        raise ValueError(f"Physician entry for {name} missing url.")
    profile_url = urljoin(BASE_URL, profile_url)

    address = (
        physician.get("address") if isinstance(physician.get("address"), dict) else {}
    )
    clinic = (
        _normalize_text(physician.get("description")) or f"{specialty} public listing"
    )
    area = _normalize_text(address.get("streetAddress")) or _normalize_text(
        physician.get("areaServed")
    )
    city = "Alexandria"

    return {
        "full_name": name,
        "specialty": specialty,
        "clinic": clinic,
        "area": area,
        "city": city,
        "source_name": SOURCE_NAME,
        "source_url": profile_url,
        "booking_url": profile_url,
    }


def build_seed() -> dict[str, Any]:
    client = httpx.Client(
        timeout=60,
        follow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            )
        },
    )
    records_by_url: dict[str, dict[str, str | None]] = {}
    source_pages: dict[str, str] = {}

    for specialty, page_url in SPECIALTY_PAGES.items():
        response = client.get(page_url)
        response.raise_for_status()
        source_pages[specialty] = page_url
        for physician in _extract_physicians(response.text):
            entry = _doctor_entry(physician, specialty)
            records_by_url.setdefault(entry["source_url"], entry)

    doctors = sorted(
        records_by_url.values(),
        key=lambda item: (
            str(item.get("specialty") or ""),
            str(item.get("full_name") or ""),
        ),
    )
    return {
        "metadata": {
            "dataset_name": "alexandria_public_directory_seed",
            "source_name": SOURCE_NAME,
            "focus": (
                "Alexandria public specialist directory coverage with "
                "reproducible page mapping."
            ),
            "captured_on": date.today().isoformat(),
            "specialty_pages": source_pages,
            "notes": [
                (
                    "Generated from public Vezeeta specialty pages using "
                    "structured JSON-LD physician entries."
                ),
                (
                    "Each row preserves source provenance so doctor "
                    "recommendations remain explainable."
                ),
                (
                    "This file is the canonical team seed source for "
                    "doctor directory data."
                ),
            ],
        },
        "doctors": doctors,
    }


def main() -> int:
    args = parse_args()
    payload = build_seed()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f'Wrote {len(payload["doctors"])} doctors to {output_path}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
