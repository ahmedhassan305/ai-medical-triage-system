from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized or chunk_size <= 0:
        return []

    safe_overlap = max(0, min(overlap, chunk_size - 1))
    sections = [
        segment.strip() for segment in _split_sections(normalized) if segment.strip()
    ]
    if not sections:
        sections = [normalized]

    chunks: list[str] = []
    current = ""
    for section in sections:
        candidate = section if not current else f"{current}\n\n{section}"
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())
            overlap_text = current[-safe_overlap:].strip() if safe_overlap else ""
            current = (
                f"{overlap_text}\n\n{section}".strip() if overlap_text else section
            )
        else:
            chunks.extend(_split_hard(section, chunk_size, safe_overlap))
            current = ""

        while len(current) > chunk_size:
            forced = _split_hard(current, chunk_size, safe_overlap)
            chunks.append(forced[0])
            current = forced[1] if len(forced) > 1 else ""

    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def _split_sections(text: str) -> list[str]:
    parts = re.split(r"\n{2,}", text)
    sections: list[str] = []
    for part in parts:
        cleaned = " ".join(part.split())
        if cleaned:
            sections.append(cleaned)
    return sections


def _split_hard(text: str, chunk_size: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - overlap
    return chunks
