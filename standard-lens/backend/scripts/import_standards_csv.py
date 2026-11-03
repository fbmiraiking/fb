"""Import standards from a CSV file."""

import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.standards_csv import DEFAULT_CSV_PATH, import_standards_csv


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help=f"CSV path (default: {DEFAULT_CSV_PATH})",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        count = import_standards_csv(db, args.csv_path)
        print(f"[import] processed {count} standards from {args.csv_path}", flush=True)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
