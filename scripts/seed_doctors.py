#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy.orm import Session

project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.db.session import engine  # noqa: E402
from app.services.doctor_seed_importer import (  # noqa: E402
    import_seed_records,
    load_seed_records,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = (
    backend_dir / "data" / "doctors" / "alexandria_public_directory_seed.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Import the canonical Alexandria/Egypt public doctor directory seed "
            "into doctor_profiles."
        )
    )
    parser.add_argument(
        "--seed-file",
        default=str(DEFAULT_SEED_PATH),
        help="Path to the curated doctor seed JSON file.",
    )
    parser.add_argument(
        "--skip-clean-legacy",
        action="store_true",
        help="Keep legacy fake seed rows instead of deleting them before import.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seed_path = Path(args.seed_file).resolve()
    if not seed_path.exists():
        logger.error("Seed file not found: %s", seed_path)
        return 1

    records = load_seed_records(seed_path)
    logger.info("Loaded %s doctor directory entries from %s", len(records), seed_path)

    with Session(engine) as db:
        result = import_seed_records(
            db,
            records,
            clean_legacy=not args.skip_clean_legacy,
        )

    logger.info(
        "Doctor seed import complete: inserted=%s updated=%s removed_legacy=%s total_seed_records=%s",
        result.inserted,
        result.updated,
        result.removed_legacy,
        result.total_seed_records,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
