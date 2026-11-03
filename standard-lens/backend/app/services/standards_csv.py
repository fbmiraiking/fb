"""CSV export/import for the standard catalog bootstrap."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_DIR
from app.db.session import SessionLocal
from app.models.standard import Standard, StandardStatus
from app.utils.standard_no import StandardNoNormalizer

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = BACKEND_DIR / "data" / "standards.csv"
CSV_COLUMNS = (
    "standard_no",
    "normalized_no",
    "standard_name",
    "standard_type",
    "status",
    "publish_date",
    "effective_date",
    "expiry_date",
    "standard_year",
    "scope",
    "source",
    "source_url",
)
_OPTIONAL_COLUMNS = (
    "standard_type",
    "publish_date",
    "effective_date",
    "expiry_date",
    "standard_year",
    "scope",
    "source_url",
)
_BATCH_SIZE = 1000


@dataclass(frozen=True, slots=True)
class CsvSeedResult:
    status: str
    imported: int = 0
    path: str = ""


def _date_text(value: date | None) -> str:
    return value.isoformat() if value is not None else ""


def _parse_date(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    return date.fromisoformat(text[:10])


def _parse_int(value: str | None) -> int | None:
    text = (value or "").strip()
    if not text:
        return None
    return int(text)


def _parse_status(value: str | None) -> StandardStatus:
    text = (value or "").strip().upper()
    try:
        return StandardStatus(text)
    except ValueError:
        return StandardStatus.UNKNOWN


def _row_to_values(row: dict[str, str]) -> dict[str, object]:
    standard_no = (row.get("standard_no") or "").strip()
    standard_name = (row.get("standard_name") or "").strip()
    if not standard_no or not standard_name:
        raise ValueError("standard_no and standard_name are required")

    normalized_no = (row.get("normalized_no") or "").strip()
    if not normalized_no:
        normalized_no = StandardNoNormalizer.normalize(standard_no)

    return {
        "standard_no": standard_no,
        "normalized_no": normalized_no,
        "standard_name": standard_name,
        "standard_type": (row.get("standard_type") or "").strip() or None,
        "status": _parse_status(row.get("status")),
        "publish_date": _parse_date(row.get("publish_date")),
        "effective_date": _parse_date(row.get("effective_date")),
        "expiry_date": _parse_date(row.get("expiry_date")),
        "standard_year": _parse_int(row.get("standard_year")),
        "scope": (row.get("scope") or "").strip() or None,
        "source": (row.get("source") or "").strip() or "std_samr",
        "source_url": (row.get("source_url") or "").strip() or None,
    }


def export_standards_csv(
    db: Session,
    output_path: Path = DEFAULT_CSV_PATH,
) -> int:
    """Write all standards to a deterministic UTF-8 CSV and return row count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    count = 0

    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for standard in db.scalars(
            select(Standard).order_by(Standard.id).execution_options(yield_per=1000)
        ):
            writer.writerow(
                {
                    "standard_no": standard.standard_no,
                    "normalized_no": standard.normalized_no,
                    "standard_name": standard.standard_name,
                    "standard_type": standard.standard_type or "",
                    "status": standard.status.value,
                    "publish_date": _date_text(standard.publish_date),
                    "effective_date": _date_text(standard.effective_date),
                    "expiry_date": _date_text(standard.expiry_date),
                    "standard_year": standard.standard_year or "",
                    "scope": standard.scope or "",
                    "source": standard.source or "",
                    "source_url": standard.source_url or "",
                }
            )
            count += 1

    temporary.replace(output_path)
    return count


def _chunks(rows: list[dict[str, object]], size: int):
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _bulk_upsert(db: Session, rows: list[dict[str, object]]) -> None:
    dialect = db.get_bind().dialect.name
    if dialect == "mysql":
        for chunk in _chunks(rows, _BATCH_SIZE):
            statement = mysql_insert(Standard).values(chunk)
            updates: dict[str, object] = {}
            for column in CSV_COLUMNS:
                if column == "normalized_no":
                    continue
                inserted = getattr(statement.inserted, column)
                if column in _OPTIONAL_COLUMNS:
                    updates[column] = func.coalesce(inserted, getattr(Standard, column))
                else:
                    updates[column] = inserted
            updates["updated_at"] = func.now()
            db.execute(statement.on_duplicate_key_update(**updates))
    elif dialect == "sqlite":
        for chunk in _chunks(rows, _BATCH_SIZE):
            statement = sqlite_insert(Standard).values(chunk)
            updates: dict[str, object] = {}
            for column in CSV_COLUMNS:
                if column == "normalized_no":
                    continue
                excluded = getattr(statement.excluded, column)
                if column in _OPTIONAL_COLUMNS:
                    updates[column] = func.coalesce(excluded, getattr(Standard, column))
                else:
                    updates[column] = excluded
            db.execute(
                statement.on_conflict_do_update(
                    index_elements=[Standard.normalized_no],
                    set_=updates,
                )
            )
    else:
        # Slow fallback for unusual test/development dialects.
        from app.sync.upsert import upsert_standard

        for row in rows:
            upsert_standard(db, row)


def import_standards_csv(
    db: Session,
    csv_path: Path = DEFAULT_CSV_PATH,
) -> int:
    """Import a standards CSV in one transaction. Returns processed row count."""
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)

    rows: list[dict[str, object]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header")
        missing = {"standard_no", "standard_name"} - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")
        for line_number, row in enumerate(reader, start=2):
            try:
                rows.append(_row_to_values(row))
            except Exception as exc:  # noqa: BLE001 - include row context
                raise ValueError(f"CSV line {line_number}: {exc}") from exc

    if not rows:
        return 0

    try:
        _bulk_upsert(db, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(rows)


def ensure_standards_seeded(
    db: Session,
    csv_path: Path = DEFAULT_CSV_PATH,
) -> CsvSeedResult:
    """Import the bundled CSV only when the standard table is empty."""
    existing = db.scalar(select(func.count()).select_from(Standard)) or 0
    if existing:
        return CsvSeedResult(status="skipped", path=str(csv_path))
    if not csv_path.exists():
        return CsvSeedResult(status="missing", path=str(csv_path))

    imported = import_standards_csv(db, csv_path)
    logger.info("Imported %d standards from %s", imported, csv_path)
    return CsvSeedResult(status="imported", imported=imported, path=str(csv_path))


def seed_standards_from_csv(
    csv_path: Path = DEFAULT_CSV_PATH,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> CsvSeedResult:
    """Open a session and seed the catalog; suitable for startup threadpool."""
    db = session_factory()
    try:
        return ensure_standards_seeded(db, csv_path)
    finally:
        db.close()
