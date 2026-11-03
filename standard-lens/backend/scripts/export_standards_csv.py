"""Export all standards to backend/data/standards.csv."""

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.standards_csv import DEFAULT_CSV_PATH, export_standards_csv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"Output CSV path (default: {DEFAULT_CSV_PATH})",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        count = export_standards_csv(db, args.output)
        print(f"[export] wrote {count} standards to {args.output}", flush=True)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
