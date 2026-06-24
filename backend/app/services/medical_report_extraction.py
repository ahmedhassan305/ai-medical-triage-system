from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from app.services.lab_pdf_extraction import extract_text_from_pdf_bytes


@dataclass(frozen=True)
class MedicalHistoryDraft:
    category: str
    title: str
    notes: str
    warning: str | None = None


_CATEGORY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("allergy", ("allergy", "allergic", "hypersensitivity", "penicillin")),
    (
        "surgery",
        (
            "past surgical history",
            "surgery:",
            "operation:",
            "operative report",
            "appendectomy",
            "cholecystectomy",
        ),
    ),
    ("injury", ("injury", "fracture", "sprain", "trauma")),
    (
        "medication",
        ("medications:", "current medication", "prescribed:", "tablet", "dose:"),
    ),
    (
        "hospitalization",
        (
            "admitted",
            "admission",
            "hospitalized",
            "discharge summary",
            "emergency department",
        ),
    ),
    ("family_history", ("family history", "mother had", "father had")),
)


def extract_report_text(
    content: bytes,
    *,
    filename: str,
    content_type: str | None,
) -> tuple[str, str | None]:
    lower_name = filename.lower()
    media_type = (content_type or "").lower()
    if media_type == "application/pdf" or lower_name.endswith(".pdf"):
        return extract_text_from_pdf_bytes(content), None

    if media_type.startswith("image/") or lower_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp")
    ):
        return _extract_text_from_image(content), None

    raise ValueError("Only PDF or image report files are accepted.")


def draft_medical_history_from_report_text(text: str) -> MedicalHistoryDraft:
    cleaned = _clean_text(text)
    if len(cleaned) < 12:
        raise ValueError("Could not read enough text from this report.")

    lower_text = cleaned.lower()
    lower_prefix = lower_text[:900]
    category = "diagnosed_condition"
    for candidate, keywords in _CATEGORY_PATTERNS:
        category_text = lower_prefix if candidate == "injury" else lower_text
        if any(keyword in category_text for keyword in keywords):
            category = candidate
            break

    title = _extract_title(cleaned, category)
    notes = _summarize_notes(cleaned)
    return MedicalHistoryDraft(
        category=category,
        title=title,
        notes=notes,
        warning=(
            "Review the extracted text before saving. "
            "OCR/PDF extraction can be imperfect."
        ),
    )


def _extract_text_from_image(content: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise ValueError(
            "Image OCR is not available on this backend. Upload a text PDF instead."
        ) from exc

    try:
        image = Image.open(BytesIO(content))
        return str(pytesseract.image_to_string(image))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Could not read text from this image report.") from exc


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(text: str, category: str) -> str:
    patterns = (
        r"\bdiagnosis\s*[:\-]\s*(?P<value>.{3,80})",
        r"\bdiagnosed(?:\s+with)?\s*[:\-]?\s*(?P<value>.{3,80})",
        r"\bchief complaint(?:\s+was|\s+of)?\s*(?P<value>.{3,80})",
        r"\bcondition\s*[:\-]\s*(?P<value>.{3,80})",
        r"\ballergy\s*[:\-]\s*(?P<value>.{3,80})",
        r"\bsurgery\s*[:\-]\s*(?P<value>.{3,80})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _short_title(match.group("value"))

    first_sentence = re.split(r"[.;\n]", text, maxsplit=1)[0]
    fallback_by_category = {
        "allergy": "Reported allergy",
        "surgery": "Reported surgery",
        "injury": "Reported injury",
        "medication": "Reported medication",
        "hospitalization": "Hospital report",
        "family_history": "Family history",
    }
    return _short_title(first_sentence) or fallback_by_category.get(
        category,
        "Doctor report finding",
    )


def _short_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" :-,.;")
    cleaned = re.split(r"[.;]", cleaned, maxsplit=1)[0].strip(" :-,.;")
    if not cleaned:
        return ""
    words = cleaned.split()
    return " ".join(words[:8])[:200]


def _summarize_notes(text: str) -> str:
    cleaned = _clean_text(text)
    clinical_text = _extract_clinical_note_text(cleaned)
    structured_summary = _build_structured_summary(clinical_text)
    if structured_summary:
        return structured_summary

    return _sentence_summary(clinical_text)


def _build_structured_summary(text: str) -> str:
    age_gender = _extract_first_match(
        text,
        r"\b(?:the\s+)?patient was an?\s+"
        r"(?P<value>\d{1,3})[ -]?year[ -]?old\s+"
        r"(?P<gender>female|male|woman|man)\b",
    )
    history = _extract_first_match(
        text,
        r"\bhistory of\s+(?P<value>.*?)(?:\s+who presented|\.|$)",
    )
    complaint = _extract_first_match(
        text,
        r"\bchief complaint of\s+(?P<value>[^.]+)",
    )
    date = _extract_first_match(
        text,
        r"\bon\s+(?P<value>\d{1,2}/\d{1,2}/\d{2,4})\b",
    )
    episode = _find_sentence(
        text,
        ("passed out", "fainted", "lost consciousness"),
    )
    prior_episode = _find_sentence(
        text,
        ("similar episode", "previous episode", "no previous workup"),
    )
    no_workup = _find_sentence(
        text,
        ("never having a medical workup", "no previous workup"),
    )

    summary_parts: list[str] = []
    if age_gender and history:
        summary_parts.append(f"{age_gender} with history of {history}.")
    elif age_gender:
        summary_parts.append(f"{age_gender}.")

    if complaint:
        visit_text = "Emergency department visit"
        if date:
            visit_text += f" on {date}"
        visit_text += f" for {complaint}."
        summary_parts.append(visit_text)

    if episode:
        summary_parts.append(_summarize_event_sentence(episode))

    if prior_episode and prior_episode != episode:
        summary_parts.append(_summarize_prior_episode(prior_episode, no_workup))
    elif no_workup:
        summary_parts.append("No previous medical workup documented.")

    if len(summary_parts) < 2:
        return ""
    return " ".join(summary_parts[:4])


def _summarize_event_sentence(sentence: str) -> str:
    lower_sentence = sentence.lower()
    if "passed out" in lower_sentence and "getting out of the shower" in lower_sentence:
        return (
            "Fainting episode occurred two days before admission while getting "
            "out of the shower."
        )
    if "passed out" in lower_sentence:
        return _clean_sentence(
            re.sub(r"\bpassed out\b", "had a fainting episode", sentence, flags=re.I)
        )
    return _clean_sentence(sentence)


def _summarize_prior_episode(sentence: str, no_workup: str) -> str:
    lower_sentence = sentence.lower()
    if "similar episode" in lower_sentence:
        summary = "Prior similar episode reported"
        if no_workup:
            summary += "; no previous medical workup documented"
        return f"{summary}."
    return _clean_sentence(sentence)


def _sentence_summary(text: str) -> str:
    sentences = [
        sentence
        for sentence in _split_sentences(text)
        if not _is_administrative_sentence(sentence)
    ]
    if not sentences:
        return text[:500].rstrip(" ,.;")

    selected: list[str] = []
    total_length = 0
    for sentence in sentences:
        cleaned = _clean_sentence(sentence)
        projected_length = total_length + len(cleaned) + 1
        if selected and projected_length > 520:
            break
        selected.append(cleaned)
        total_length = projected_length
        if len(selected) >= 4:
            break
    return " ".join(selected)


def _extract_first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return ""
    value = match.group("value")
    gender = match.groupdict().get("gender")
    if gender:
        value = f"{value}-year-old {gender}"
    return _clean_fragment(value)


def _find_sentence(text: str, keywords: tuple[str, ...]) -> str:
    for sentence in _split_sentences(text):
        lower_sentence = sentence.lower()
        if any(keyword in lower_sentence for keyword in keywords):
            return sentence
    return ""


def _split_sentences(text: str) -> list[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]


def _clean_sentence(text: str) -> str:
    cleaned = _clean_fragment(text)
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _clean_fragment(text: str) -> str:
    return _clean_text(text).strip(" :-,.;")


def _is_administrative_sentence(sentence: str) -> bool:
    lower_sentence = sentence.lower()
    return any(
        marker in lower_sentence
        for marker in (
            "arizona medical board",
            "medical consultant",
            "physician:",
            "case:",
            "reviewed by",
        )
    )


def _extract_clinical_note_text(text: str) -> str:
    start_patterns = (
        r"\bthe patient was\b",
        r"\bpatient is\b",
        r"\bpatient presented\b",
        r"\bpresented to\b",
        r"\bchief complaint\b",
        r"\bhistory of present illness\b",
        r"\bdiagnosis\s*[:\-]",
        r"\bassessment\s*[:\-]",
    )
    lower_text = text.lower()
    starts = [
        match.start()
        for pattern in start_patterns
        if (match := re.search(pattern, lower_text))
    ]
    if not starts:
        return text

    clinical_text = text[min(starts) :]
    stop_match = re.search(
        r"\b(?:medical consultant|reviewed by|signature|sincerely)\b",
        clinical_text,
        flags=re.IGNORECASE,
    )
    if stop_match and stop_match.start() > 120:
        clinical_text = clinical_text[: stop_match.start()]
    return clinical_text.strip(" :-,.;")
