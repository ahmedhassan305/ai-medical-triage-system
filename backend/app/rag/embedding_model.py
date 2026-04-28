from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_MODEL_LOCK = threading.Lock()
_MODEL: SentenceTransformer | Any | None = None
_MODEL_NAME: str | None = None


def get_embedding_model() -> SentenceTransformer:
    global _MODEL
    global _MODEL_NAME

    settings = get_settings()
    model_name = settings.rag_embed_model

    if _MODEL is not None and _MODEL_NAME == model_name:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is None or _MODEL_NAME != model_name:
            from sentence_transformers import SentenceTransformer

            _MODEL = SentenceTransformer(model_name)
            _MODEL_NAME = model_name
        return _MODEL


def clear_embedding_model_cache() -> None:
    global _MODEL
    global _MODEL_NAME
    with _MODEL_LOCK:
        _MODEL = None
        _MODEL_NAME = None
