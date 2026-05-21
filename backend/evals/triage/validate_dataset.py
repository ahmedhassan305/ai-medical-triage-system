from __future__ import annotations

import argparse
import json
from pathlib import Path

from evals.triage.models import TriageEvalCase


def load_jsonl(path: Path) -> list[TriageEvalCase]:
    cases: list[TriageEvalCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        payload = json.loads(line)
        try:
            cases.append(TriageEvalCase.model_validate(payload))
        except Exception as exc:
            raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a triage JSONL dataset.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    cases = load_jsonl(args.dataset)
    ids = [case.id for case in cases]
    duplicate_ids = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicate_ids:
        raise ValueError(f"duplicate case ids: {', '.join(duplicate_ids)}")

    print(f"validated_cases={len(cases)}")
    print(f"dataset={args.dataset}")


if __name__ == "__main__":
    main()
