from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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


def preload_embedding_model() -> None:
    """Warm the embedding model so first patient request does not pay load cost."""
    try:
        settings = get_settings()
        logger.info("preloading_embedding_model model=%s", settings.rag_embed_model)
        get_embedding_model()
        logger.info("embedding_model_preloaded model=%s", settings.rag_embed_model)
    except Exception as exc:
        logger.warning("embedding_model_preload_failed error=%s", exc)
