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


def _to_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _split_kv(value: str | None) -> dict[str, float]:
    if not value:
        return {}

    result: dict[str, float] = {}
    for part in value.split(","):
        item = part.strip()
        if not item or "=" not in item:
            continue
        key, raw = item.split("=", 1)
        try:
            result[key.strip()] = float(raw.strip())
        except ValueError:
            continue
    return result


@dataclass(frozen=True)
class Settings:
    app_env: str
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
    triage_enable_embedding_signal: bool
    triage_rate_limit_count: int
    triage_rate_limit_window_seconds: int
    auth_rate_limit_count: int
    auth_rate_limit_window_seconds: int
    rag_dense_weight: float
    rag_sparse_weight: float
    rag_rerank_weight: float
    rag_source_priorities: dict[str, float]


@lru_cache
def get_settings() -> Settings:
    tfidf_ngram_min = _to_int(os.getenv("TFIDF_NGRAM_MIN"), 1)
    tfidf_ngram_max = _to_int(os.getenv("TFIDF_NGRAM_MAX"), 2)
    if tfidf_ngram_min > tfidf_ngram_max:
        tfidf_ngram_min, tfidf_ngram_max = tfidf_ngram_max, tfidf_ngram_min

    return Settings(
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
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
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
        reasoner_mode=os.getenv("REASONER_MODE", "ollama").strip().lower(),
        strict_reasoner=_to_bool(os.getenv("STRICT_REASONER"), False),
        patient_history_visit_limit=_to_int(
            os.getenv("PATIENT_HISTORY_VISIT_LIMIT"), 10
        ),
        patient_history_top_matches=_to_int(
            os.getenv("PATIENT_HISTORY_TOP_MATCHES"),
            3,
        ),
        triage_enable_embedding_signal=_to_bool(
            os.getenv("TRIAGE_ENABLE_EMBEDDING_SIGNAL"),
            False,
        ),
        triage_rate_limit_count=_to_int(os.getenv("TRIAGE_RATE_LIMIT_COUNT"), 30),
        triage_rate_limit_window_seconds=_to_int(
            os.getenv("TRIAGE_RATE_LIMIT_WINDOW_SECONDS"),
            60,
        ),
        auth_rate_limit_count=_to_int(os.getenv("AUTH_RATE_LIMIT_COUNT"), 10),
        auth_rate_limit_window_seconds=_to_int(
            os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS"),
            60,
        ),
        rag_dense_weight=_to_float(os.getenv("RAG_DENSE_WEIGHT"), 0.45),
        rag_sparse_weight=_to_float(os.getenv("RAG_SPARSE_WEIGHT"), 0.35),
        rag_rerank_weight=_to_float(os.getenv("RAG_RERANK_WEIGHT"), 0.20),
        rag_source_priorities=_split_kv(
            os.getenv("RAG_SOURCE_PRIORITIES", "NHS=1.15,Mayo Clinic=1.0,Unknown=0.9")
        ),
    )
