from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedLabValue:
    lab_name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None


LAB_PATTERNS: dict[str, list[str]] = {
    "Hemoglobin": [r"\b(?:hemoglobin|hb)\b"],
    "WBC": [r"\b(?:wbc|white blood cells?)\b"],
    "RBC": [r"\b(?:rbc|red blood cells?)\b"],
    "Platelets": [r"\b(?:platelets?|plt)\b"],
    "Glucose": [r"\bglucose\b"],
    "HbA1c": [r"\b(?:hba1c|a1c)\b"],
    "Creatinine": [r"\bcreatinine\b"],
    "Urea/BUN": [r"\b(?:urea|bun)\b"],
    "ALT": [r"\balt\b"],
    "AST": [r"\bast\b"],
    "CRP": [r"\bcrp\b"],
    "ESR": [r"\besr\b"],
    "Cholesterol": [r"\bcholesterol\b"],
    "LDL": [r"\bldl\b"],
    "HDL": [r"\bhdl\b"],
    "Triglycerides": [r"\btriglycerides?\b"],
    "Sodium": [r"\bsodium\b"],
    "Potassium": [r"\bpotassium\b"],
    "TSH": [r"\btsh\b"],
}

VALUE_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z/%]+(?:/[a-zA-Z]+)?)?",
    re.IGNORECASE,
)


def extract_text_from_pdf_bytes(content: bytes) -> str:
    if not content.startswith(b"%PDF"):
        raise ValueError("Only PDF files are accepted.")
    text = content.decode("latin-1", errors="ignore")
    text = re.sub(r"\\[nr]", "\n", text)
    text = re.sub(r"[()<>]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_lab_values_from_text(text: str) -> list[ExtractedLabValue]:
    values: list[ExtractedLabValue] = []
    seen: set[str] = set()
    for lab_name, aliases in LAB_PATTERNS.items():
        for alias in aliases:
            match = re.search(
                rf"{alias}\s*[:=\-]?\s*(?P<trailing>.{{0,80}})",
                text,
                flags=re.IGNORECASE,
            )
            if not match:
                continue
            value_match = VALUE_PATTERN.search(match.group("trailing"))
            if not value_match:
                continue
            if lab_name in seen:
                break
            seen.add(lab_name)
            values.append(
                ExtractedLabValue(
                    lab_name=lab_name,
                    value=value_match.group("value"),
                    unit=value_match.group("unit"),
                )
            )
            break
    return values


def extract_lab_values_from_pdf(content: bytes) -> list[ExtractedLabValue]:
    return extract_lab_values_from_text(extract_text_from_pdf_bytes(content))
