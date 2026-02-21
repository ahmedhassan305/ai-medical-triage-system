from __future__ import annotations


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    normalized = text.strip()
    if not normalized or chunk_size <= 0:
        return []

    safe_overlap = max(0, min(overlap, chunk_size - 1))
    chunks: list[str] = []

    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = end - safe_overlap

    return chunks
