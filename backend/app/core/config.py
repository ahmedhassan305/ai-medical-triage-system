from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


DEFAULT_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
]


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _normalize_api_prefix(value: str | None) -> str:
    prefix = (value or "/api/v1").strip()
    if not prefix.startswith("/"):
        prefix = f"/{prefix}"
    return prefix.rstrip("/") or "/api/v1"


def _to_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    api_v1_prefix: str
    cors_origins: list[str]
    log_level: str
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    db_auto_create: bool
    rag_data_dir: str
    rag_retriever: str
    rag_top_k: int
    tfidf_max_features: int
    tfidf_ngram_min: int
    tfidf_ngram_max: int
    rag_embed_model: str
    rag_cache_dir: str
    rag_chunk_size: int
    rag_chunk_overlap: int
    rag_rebuild_index: bool
    ollama_host: str
    ollama_model: str
    reasoner_mode: str
    strict_reasoner: bool
    patient_history_visit_limit: int
    patient_history_top_matches: int


@lru_cache
def get_settings() -> Settings:
    tfidf_ngram_min = _to_int(os.getenv("TFIDF_NGRAM_MIN"), 1)
    tfidf_ngram_max = _to_int(os.getenv("TFIDF_NGRAM_MAX"), 2)
    if tfidf_ngram_min > tfidf_ngram_max:
        tfidf_ngram_min, tfidf_ngram_max = tfidf_ngram_max, tfidf_ngram_min

    return Settings(
        app_name=os.getenv("APP_NAME", "AI Medical Triage System API"),
        api_v1_prefix=_normalize_api_prefix(os.getenv("API_V1_PREFIX")),
        cors_origins=_split_csv(os.getenv("CORS_ORIGINS")) or DEFAULT_DEV_CORS_ORIGINS,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./triage.db"),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_access_token_expire_minutes=_to_int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES"),
            60,
        ),
        db_auto_create=_to_bool(os.getenv("DB_AUTO_CREATE"), False),
        rag_data_dir=os.getenv("RAG_DATA_DIR", "./data"),
        rag_retriever=os.getenv("RAG_RETRIEVER", "stub").strip().lower(),
        rag_top_k=_to_int(os.getenv("RAG_TOP_K"), 3),
        tfidf_max_features=_to_int(os.getenv("TFIDF_MAX_FEATURES"), 1000),
        tfidf_ngram_min=tfidf_ngram_min,
        tfidf_ngram_max=tfidf_ngram_max,
        rag_embed_model=os.getenv(
            "RAG_EMBED_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
        rag_cache_dir=os.getenv("RAG_CACHE_DIR", "./.cache/rag"),
        rag_chunk_size=_to_int(os.getenv("RAG_CHUNK_SIZE"), 2000),
        rag_chunk_overlap=_to_int(os.getenv("RAG_CHUNK_OVERLAP"), 200),
        rag_rebuild_index=_to_bool(os.getenv("RAG_REBUILD_INDEX"), False),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4"),
        reasoner_mode=os.getenv("REASONER_MODE", "ollama").strip().lower(),
        strict_reasoner=_to_bool(os.getenv("STRICT_REASONER"), False),
        patient_history_visit_limit=_to_int(
            os.getenv("PATIENT_HISTORY_VISIT_LIMIT"), 10
        ),
        patient_history_top_matches=_to_int(
            os.getenv("PATIENT_HISTORY_TOP_MATCHES"),
            3,
        ),
    )
