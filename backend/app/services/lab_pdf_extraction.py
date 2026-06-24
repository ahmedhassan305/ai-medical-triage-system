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

    text = _extract_text_with_pymupdf(content)
    if _has_usable_pdf_text(text):
        return _normalize_pdf_text(text)

    fallback_text = _extract_text_with_plain_fallback(content)
    if _has_usable_pdf_text(fallback_text):
        return _normalize_pdf_text(fallback_text)

    raise ValueError("Could not read selectable text from this PDF.")


def _extract_text_with_pymupdf(content: bytes) -> str:
    try:
        import fitz
    except ModuleNotFoundError:
        return ""

    try:
        document = fitz.open(stream=content, filetype="pdf")
        return "\n".join(page.get_text("text") for page in document)
    except Exception:  # noqa: BLE001
        return ""


def _extract_text_with_plain_fallback(content: bytes) -> str:
    text = content.decode("latin-1", errors="ignore")
    text = re.sub(r"\\[nr]", "\n", text)
    text = re.sub(r"[()<>]", " ", text)
    return text


def _has_usable_pdf_text(text: str) -> bool:
    cleaned = _normalize_pdf_text(text)
    if len(cleaned) < 12:
        return False
    raw_pdf_markers = sum(
        cleaned.count(marker)
        for marker in (
            " obj ",
            " endobj ",
            " stream ",
            "/Type",
            "/Filter",
            "/Root",
            "xref",
            "startxref",
        )
    )
    return not (cleaned.lstrip().startswith("%PDF") and raw_pdf_markers >= 3)


def _normalize_pdf_text(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
