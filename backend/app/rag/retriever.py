from __future__ import annotations

from typing import Protocol


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[str]: ...


class StubRetriever:
    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        return []
