from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.rag.embedding_retriever import EmbeddingRetriever
from app.rag.retriever import RetrievedChunk, Retriever, StubRetriever
from app.rag.tfidf_retriever import TfidfRetriever


@dataclass
class EvalRow:
    query: str
    relevant_doc_ids: list[str]
    notes: str = ""


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def _overlap_score(query: str, chunk_text: str) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0
    chunk_tokens = _tokenize(chunk_text)
    if not chunk_tokens:
        return 0.0
    common = query_tokens.intersection(chunk_tokens)
    return len(common) / len(query_tokens)


def _llm_judge_score(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    host: str,
    model: str,
) -> float:
    context = "\n\n".join(chunk.text for chunk in chunks[:3]) or "No context."
    prompt = (
        "Score context relevance for a medical query from 0 to 1.\n"
        f"Query: {query}\n\nContext:\n{context}\n\n"
        "Respond with only a numeric score."
    )
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        response = httpx.post(
            f"{host.rstrip('/')}/api/generate", json=payload, timeout=15
        )
        response.raise_for_status()
        text = str(response.json().get("response", "")).strip()
        value = float(text.split()[0])
        return max(0.0, min(1.0, value))
    except Exception:
        return 0.0


def _build_retriever(name: str, settings_data_dir: str) -> Retriever:
    settings = get_settings()
    if name == "stub":
        return StubRetriever()
    if name == "tfidf":
        return TfidfRetriever(
            data_dir=settings_data_dir,
            max_features=settings.tfidf_max_features,
            ngram_range=(settings.tfidf_ngram_min, settings.tfidf_ngram_max),
        )
    return EmbeddingRetriever(
        data_dir=settings_data_dir,
        chunk_size=settings.rag_chunk_size,
        overlap=settings.rag_chunk_overlap,
        top_k=settings.rag_top_k,
    )


def _load_eval_rows(path: Path) -> list[EvalRow]:
    rows: list[EvalRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        rows.append(
            EvalRow(
                query=str(payload.get("query", "")).strip(),
                relevant_doc_ids=list(payload.get("relevant_doc_ids", [])),
                notes=str(payload.get("notes", "")).strip(),
            )
        )
    return [row for row in rows if row.query and row.relevant_doc_ids]


def run(k: int, retriever_name: str, llm_judge: bool) -> dict[str, object]:
    settings = get_settings()
    backend_dir = Path(__file__).resolve().parents[3]
    dataset_path = Path(__file__).resolve().with_name("eval_dataset.jsonl")
    report_path = backend_dir / "reports" / "rag_eval_report.json"

    rows = _load_eval_rows(dataset_path)
    retriever = _build_retriever(retriever_name, settings.rag_data_dir)

    hits = 0
    relevance_scores: list[float] = []
    per_query: list[dict[str, object]] = []

    for row in rows:
        chunks = retriever.retrieve_chunks(row.query, top_k=k)
        retrieved_doc_ids = [chunk.doc_id for chunk in chunks]
        hit = any(doc_id in row.relevant_doc_ids for doc_id in retrieved_doc_ids)
        if hit:
            hits += 1

        if llm_judge:
            relevance = _llm_judge_score(
                row.query,
                chunks,
                host=settings.ollama_host,
                model=settings.ollama_model,
            )
        else:
            overlap_values = [_overlap_score(row.query, chunk.text) for chunk in chunks]
            relevance = (
                sum(overlap_values) / len(overlap_values) if overlap_values else 0.0
            )
        relevance_scores.append(relevance)

        per_query.append(
            {
                "query": row.query,
                "relevant_doc_ids": row.relevant_doc_ids,
                "retrieved_doc_ids": retrieved_doc_ids,
                "hit": hit,
                "context_relevance": relevance,
                "notes": row.notes,
            }
        )

    total = len(rows)
    recall_at_k = (hits / total) if total else 0.0
    avg_relevance = (
        (sum(relevance_scores) / len(relevance_scores)) if relevance_scores else 0.0
    )

    report = {
        "retriever": retriever_name,
        "k": k,
        "llm_judge": llm_judge,
        "total_queries": total,
        "hits": hits,
        "recall_at_k": recall_at_k,
        "context_relevance": avg_relevance,
        "dataset_path": str(dataset_path),
        "queries": per_query,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("RAG Evaluation")
    print(f"retriever:          {retriever_name}")
    print(f"k:                  {k}")
    print(f"queries:            {total}")
    print(f"hits:               {hits}")
    print(f"recall@k:           {recall_at_k:.4f}")
    print(f"context_relevance:  {avg_relevance:.4f}")
    print(f"report:             {report_path}")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG retrieval evaluation.")
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument(
        "--retriever",
        type=str,
        choices=["stub", "tfidf", "embedding"],
        default="embedding",
    )
    parser.add_argument("--llm_judge", action="store_true")
    args = parser.parse_args()

    run(k=max(1, args.k), retriever_name=args.retriever, llm_judge=args.llm_judge)


if __name__ == "__main__":
    main()
