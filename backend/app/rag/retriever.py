from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    source_file: str
    chunk_id: str
    text: str
    source: str
    title: str
    url: str
    score: float = 0.0


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[str]: ...

    def retrieve_chunks(self, query: str, top_k: int = 3) -> list[RetrievedChunk]: ...


class StubRetriever:
    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        return []

    def retrieve_chunks(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        return []
