from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.specialties import (  # noqa: E402
    TRIAGE_SPECIALTIES,
    canonicalize_specialty,
)

DATASET_PATH = ROOT / "triage_eval_all_specialties_cases.json"
RESULTS_CSV = ROOT / "triage_eval_results.csv"
SUMMARY_JSON = ROOT / "triage_eval_summary.json"

# Edit these constants or set env vars when your backend uses another host/port.
BASE_URL = os.getenv("TRIAGE_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
TRIAGE_PATH = os.getenv("TRIAGE_API_PATH", "/api/v1/triage")
CLARIFY_PATH = os.getenv("TRIAGE_CLARIFY_PATH", "/api/v1/clarify")
TIMEOUT_SECONDS = float(os.getenv("TRIAGE_EVAL_TIMEOUT", "45"))
FOLLOW_CLARIFICATION = os.getenv("TRIAGE_EVAL_FOLLOW_CLARIFICATION", "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def contains_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" for char in text)


def make_payload(case: dict[str, Any]) -> dict[str, Any]:
    text = case["input_text"]
    return {
        "query": text,
        "language": "ar" if contains_arabic(text) else "en",
        "patient_age": case.get("patient_age"),
        "patient_gender": case.get("patient_gender"),
    }


def make_clarification_payload(
    case: dict[str, Any], questions: list[dict[str, Any]]
) -> dict[str, Any]:
    text = case["input_text"]
    return {
        "original_query": text,
        "language": "ar" if contains_arabic(text) else "en",
        "patient_age": case.get("patient_age"),
        "patient_gender": case.get("patient_gender"),
        "answers": build_answers_for_questions(case, questions),
    }


def answer_lookup(case: dict[str, Any]) -> dict[str, str]:
    answers = case.get("clarification_answers", [])
    if not isinstance(answers, list):
        return {}
    lookup: dict[str, str] = {}
    for answer in answers:
        if not isinstance(answer, dict):
            continue
        question_id = answer.get("question_id")
        answer_text = answer.get("answer")
        if isinstance(question_id, str) and isinstance(answer_text, str):
            lookup[question_id.strip().lower()] = answer_text
    return lookup


def choose_answer(question: dict[str, Any], case: dict[str, Any]) -> str:
    lookup = answer_lookup(case)
    question_id = str(question.get("id", "") or "").strip()
    question_text = str(question.get("question", "") or "")
    combined = f"{question_id} {question_text}".lower()

    if question_id.lower() in lookup:
        return lookup[question_id.lower()]
    if any(token in combined for token in ("duration", "how long", "long have")):
        return lookup.get("duration", "Started recently")
    if any(token in combined for token in ("onset", "when", "start")):
        return lookup.get("onset", lookup.get("duration", "Started recently"))
    if any(token in combined for token in ("severity", "severe", "scale")):
        return lookup.get("severity", "Moderate")
    if any(
        token in combined
        for token in ("associated", "also", "other symptoms", "with it")
    ):
        return lookup.get(
            "associated_symptoms",
            case.get("expected_condition_hint", "No extra details"),
        )
    if any(token in combined for token in ("red", "danger", "weakness", "blood")):
        return lookup.get("red_flags", "No major danger signs beyond what I described")
    if any(token in combined for token in ("worse", "progress", "improving")):
        return lookup.get("progression", "Not clearly improving")
    return lookup.get("associated_symptoms", "Not sure")


def build_answers_for_questions(
    case: dict[str, Any], questions: list[dict[str, Any]]
) -> list[dict[str, str]]:
    answers: list[dict[str, str]] = []
    for index, question in enumerate(questions, start=1):
        question_id = str(question.get("id") or f"clarification_{index}")
        answers.append(
            {
                "question_id": question_id,
                "answer": choose_answer(question, case),
            }
        )
    if answers:
        return answers
    return [
        {
            "question_id": "additional_context",
            "answer": answer_lookup(case).get(
                "associated_symptoms", case["input_text"]
            ),
        }
    ]


def extract_predicted_specialty(response: dict[str, Any]) -> str | None:
    return canonicalize_specialty(response.get("recommended_specialty"))


def extract_predicted_urgency(response: dict[str, Any]) -> str | None:
    raw = response.get("urgency_level") or response.get("triage_level")
    if not isinstance(raw, str):
        return None
    urgency = raw.strip().upper()
    return urgency if urgency in {"HIGH", "MEDIUM", "LOW"} else None


def post_json(path: str, payload_data: dict[str, Any]) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    payload = json.dumps(payload_data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("API returned a non-object JSON response.")
    return parsed


def post_triage(case: dict[str, Any]) -> dict[str, Any]:
    return post_json(TRIAGE_PATH, make_payload(case))


def post_clarify(
    case: dict[str, Any], questions: list[dict[str, Any]]
) -> dict[str, Any]:
    return post_json(CLARIFY_PATH, make_clarification_payload(case, questions))


def final_response_for_scoring(
    case: dict[str, Any], response: dict[str, Any]
) -> tuple[dict[str, Any], bool]:
    questions = response.get("questions")
    if not FOLLOW_CLARIFICATION or not response.get("needs_clarification"):
        return response, False
    if not isinstance(questions, list):
        questions = []
    clarified = post_clarify(case, questions)
    triage_result = clarified.get("triage_result")
    if isinstance(triage_result, dict):
        return triage_result, True
    return clarified, True


def accuracy(correct: int, total: int) -> float:
    return round(correct / total, 4) if total else 0.0


def nested_counter_to_dict(
    counter: dict[str, Counter[str]],
) -> dict[str, dict[str, int]]:
    return {
        row_label: dict(sorted(row_counter.items()))
        for row_label, row_counter in sorted(counter.items())
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated = [row for row in rows if not row["api_error"]]
    specialty_correct = sum(row["specialty_match"] for row in evaluated)
    urgency_correct = sum(row["urgency_match"] for row in evaluated)
    exact_correct = sum(row["exact_match"] for row in evaluated)

    per_specialty: dict[str, dict[str, Any]] = {}
    for specialty in TRIAGE_SPECIALTIES:
        specialty_rows = [
            row for row in evaluated if row["expected_specialty"] == specialty
        ]
        per_specialty[specialty] = {
            "total": len(specialty_rows),
            "specialty_accuracy": accuracy(
                sum(row["specialty_match"] for row in specialty_rows),
                len(specialty_rows),
            ),
            "urgency_accuracy": accuracy(
                sum(row["urgency_match"] for row in specialty_rows),
                len(specialty_rows),
            ),
            "exact_match_accuracy": accuracy(
                sum(row["exact_match"] for row in specialty_rows),
                len(specialty_rows),
            ),
        }

    per_difficulty: dict[str, dict[str, Any]] = {}
    for difficulty in sorted({row["difficulty"] for row in rows}):
        difficulty_rows = [row for row in evaluated if row["difficulty"] == difficulty]
        per_difficulty[difficulty] = {
            "total": len(difficulty_rows),
            "specialty_accuracy": accuracy(
                sum(row["specialty_match"] for row in difficulty_rows),
                len(difficulty_rows),
            ),
            "urgency_accuracy": accuracy(
                sum(row["urgency_match"] for row in difficulty_rows),
                len(difficulty_rows),
            ),
            "exact_match_accuracy": accuracy(
                sum(row["exact_match"] for row in difficulty_rows),
                len(difficulty_rows),
            ),
        }

    specialty_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    urgency_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    for row in evaluated:
        specialty_confusion[row["expected_specialty"]][
            row["predicted_specialty"] or "UNKNOWN"
        ] += 1
        urgency_confusion[row["expected_urgency"]][
            row["predicted_urgency"] or "UNKNOWN"
        ] += 1

    return {
        "api_base_url": BASE_URL,
        "triage_path": TRIAGE_PATH,
        "clarify_path": CLARIFY_PATH,
        "follow_clarification": FOLLOW_CLARIFICATION,
        "total_cases": len(rows),
        "evaluated_cases": len(evaluated),
        "api_errors": len(rows) - len(evaluated),
        "clarification_requested": sum(
            bool(row["needs_clarification"]) for row in rows
        ),
        "clarification_followed": sum(
            bool(row["clarification_followed"]) for row in rows
        ),
        "specialty_accuracy": accuracy(specialty_correct, len(evaluated)),
        "urgency_accuracy": accuracy(urgency_correct, len(evaluated)),
        "exact_match_accuracy": accuracy(exact_correct, len(evaluated)),
        "accuracy_per_specialty": per_specialty,
        "accuracy_per_difficulty": per_difficulty,
        "specialty_confusion_matrix": nested_counter_to_dict(specialty_confusion),
        "urgency_confusion_matrix": nested_counter_to_dict(urgency_confusion),
    }


def run_eval() -> None:
    with DATASET_PATH.open("r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if not isinstance(cases, list):
        raise ValueError("Dataset root must be a JSON array.")

    rows: list[dict[str, Any]] = []
    started = time.time()
    for index, case in enumerate(cases, start=1):
        expected_specialty = case["expected_specialty"]
        expected_urgency = case["expected_urgency"]
        predicted_specialty = None
        predicted_urgency = None
        error = ""
        status = "ok"
        needs_clarification = False
        clarification_followed = False
        clarification_question_count = 0

        try:
            response = post_triage(case)
            needs_clarification = bool(response.get("needs_clarification"))
            questions = response.get("questions")
            clarification_question_count = (
                len(questions) if isinstance(questions, list) else 0
            )
            response, clarification_followed = final_response_for_scoring(
                case, response
            )
            predicted_specialty = extract_predicted_specialty(response)
            predicted_urgency = extract_predicted_urgency(response)
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            status = "api_error"
            error = str(exc)
        except Exception as exc:  # noqa: BLE001
            status = "api_error"
            error = f"{type(exc).__name__}: {exc}"

        specialty_match = predicted_specialty == expected_specialty
        urgency_match = predicted_urgency == expected_urgency
        row = {
            "case_id": case["case_id"],
            "specialty_group": case["specialty_group"],
            "difficulty": case["difficulty"],
            "patient_age": case["patient_age"],
            "patient_gender": case["patient_gender"],
            "expected_specialty": expected_specialty,
            "predicted_specialty": predicted_specialty or "",
            "expected_urgency": expected_urgency,
            "predicted_urgency": predicted_urgency or "",
            "specialty_match": specialty_match,
            "urgency_match": urgency_match,
            "exact_match": specialty_match and urgency_match,
            "needs_clarification": needs_clarification,
            "clarification_followed": clarification_followed,
            "clarification_question_count": clarification_question_count,
            "api_error": error,
            "status": status,
            "input_text": case["input_text"],
            "expected_condition_hint": case["expected_condition_hint"],
            "red_flags_present": case["red_flags_present"],
            "reason_for_label": case["reason_for_label"],
        }
        rows.append(row)

        if index % 25 == 0 or index == len(cases):
            elapsed = time.time() - started
            print(f"Processed {index}/{len(cases)} cases in {elapsed:.1f}s")

    fieldnames = list(rows[0]) if rows else []
    with RESULTS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    with SUMMARY_JSON.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"\nSaved {RESULTS_CSV.name}")
    print(f"Saved {SUMMARY_JSON.name}")
    print(f"Specialty accuracy: {summary['specialty_accuracy']}")
    print(f"Urgency accuracy: {summary['urgency_accuracy']}")
    print(f"Exact-match accuracy: {summary['exact_match_accuracy']}")
    print(f"API errors: {summary['api_errors']}")


if __name__ == "__main__":
    run_eval()
