from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MedicalCondition:
    doc_id: str
    source_file: str
    source: str
    title: str
    url: str
    sections: list[str]
    full_text: str


def load_conditions(data_dir: str) -> list[MedicalCondition]:
    directory = Path(data_dir)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"RAG data directory not found: {directory}")

    conditions: list[MedicalCondition] = []
    for json_file in sorted(directory.glob("*.json")):

        source_hint = _source_from_filename(json_file.name)
        payload = json.loads(json_file.read_text(encoding="utf-8"))
        for index, record in enumerate(_extract_records(payload)):
            condition = _to_condition(
                record,
                source_hint=source_hint,
                source_file=json_file.name,
                doc_id=f"{json_file.stem}:{index}",
            )
            if condition:
                conditions.append(condition)

    return conditions


def compute_dataset_hash(data_dir: str) -> str:
    directory = Path(data_dir)
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"RAG data directory not found: {directory}")

    digest = hashlib.sha256()
    for json_file in sorted(directory.glob("*.json")):
        digest.update(json_file.name.encode("utf-8"))
        digest.update(json_file.read_bytes())
    return digest.hexdigest()


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("conditions", "items", "data", "records", "documents"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        records: list[dict[str, Any]] = []
        for value in payload.values():
            if isinstance(value, dict):
                records.append(value)
            elif isinstance(value, list):
                records.extend(item for item in value if isinstance(item, dict))
        if records:
            return records

        return [payload]

    return []


def _to_condition(
    record: dict[str, Any],
    *,
    source_hint: str,
    source_file: str,
    doc_id: str,
) -> MedicalCondition | None:
    title = _first_text(
        record,
        ["title", "name", "condition", "condition_name", "disease", "heading"],
    )
    if not title:
        title = "Untitled condition"

    source = _first_text(record, ["source", "provider", "site"]) or source_hint
    url = _first_text(record, ["url", "link", "source_url", "page_url"]) or ""
    sections = _collect_sections(record)

    full_text = _first_text(
        record,
        ["full_text", "text", "content", "description", "overview", "summary"],
    )
    if not full_text:
        full_text = " ".join(sections)
    if not full_text:
        return None

    normalized_full_text = _normalize_spaces(f"{title}. {full_text}".strip())
    normalized_sections = [
        _normalize_spaces(section) for section in sections if section
    ]

    return MedicalCondition(
        doc_id=doc_id,
        source_file=source_file,
        source=source,
        title=title,
        url=url,
        sections=normalized_sections,
        full_text=normalized_full_text,
    )


def _collect_sections(record: dict[str, Any]) -> list[str]:
    sections: list[str] = []

    value = record.get("sections")
    if isinstance(value, dict):
        for name, section_value in value.items():
            text = _stringify(section_value)
            if text:
                sections.append(f"{_to_heading(name)}: {text}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                title = _first_text(item, ["title", "heading", "name"]) or "Section"
                text = _stringify(
                    item.get("text") or item.get("content") or item.get("value") or item
                )
                if text:
                    sections.append(f"{title}: {text}")
            else:
                text = _stringify(item)
                if text:
                    sections.append(text)

    for key in (
        "overview",
        "symptoms",
        "causes",
        "risk_factors",
        "complications",
        "diagnosis",
        "treatment",
        "prevention",
        "when_to_see_a_doctor",
        "self_care",
    ):
        if key in record:
            text = _stringify(record.get(key))
            if text:
                sections.append(f"{_to_heading(key)}: {text}")

    return sections


def _first_text(record: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = record.get(key)
        text = _stringify(value)
        if text:
            return text
    return ""


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return _normalize_spaces(value)
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        text = "; ".join(part for part in (_stringify(item) for item in value) if part)
        return _normalize_spaces(text)
    if isinstance(value, dict):
        parts: list[str] = []
        for key, raw_value in value.items():
            parsed = _stringify(raw_value)
            if parsed:
                parts.append(f"{_to_heading(str(key))}: {parsed}")
        text = "; ".join(parts)
        return _normalize_spaces(text)
    return _normalize_spaces(str(value))


def _normalize_spaces(text: str) -> str:
    return " ".join(text.split())


def _to_heading(value: str) -> str:
    return value.replace("_", " ").strip().title()


def _source_from_filename(filename: str) -> str:
    lower = filename.lower()
    if "nhs" in lower:
        return "NHS"
    if "mayo" in lower:
        return "Mayo Clinic"
    return "Unknown"
