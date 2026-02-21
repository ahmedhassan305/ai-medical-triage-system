from __future__ import annotations

import threading

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

_MODEL_LOCK = threading.Lock()
_MODEL: SentenceTransformer | None = None
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
            _MODEL = SentenceTransformer(model_name)
            _MODEL_NAME = model_name
        return _MODEL


def clear_embedding_model_cache() -> None:
    global _MODEL
    global _MODEL_NAME
    with _MODEL_LOCK:
        _MODEL = None
        _MODEL_NAME = None
