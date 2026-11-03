import csv
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.standard import Standard, StandardStatus
from app.services.standards_csv import (
    CSV_COLUMNS,
    ensure_standards_seeded,
    export_standards_csv,
    import_standards_csv,
)
from tests.factories import make_standard


def _seed(db_session: Session) -> None:
    db_session.add_all(
        [
            make_standard(
                standard_no="GB 8000-2024",
                standard_name="CSV 测试标准 A",
                status=StandardStatus.ACTIVE,
                publish_date=date(2024, 1, 1),
                effective_date=date(2024, 5, 1),
                standard_year=2024,
                scope="适用于 CSV 导入测试。",
            ),
            make_standard(
                standard_no="GB 8001-2018",
                standard_name="CSV 测试标准 B",
                status=StandardStatus.REPLACED,
                publish_date=date(2018, 1, 1),
                effective_date=date(2018, 7, 1),
                expiry_date=date(2024, 4, 30),
                standard_year=2018,
            ),
        ]
    )
    db_session.commit()


def test_export_and_import_roundtrip(db_session: Session, tmp_path) -> None:
    _seed(db_session)
    csv_path = tmp_path / "standards.csv"

    exported = export_standards_csv(db_session, csv_path)
    assert exported == 2

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert tuple(reader.fieldnames or ()) == CSV_COLUMNS
        rows = list(reader)
    assert [row["standard_no"] for row in rows] == ["GB 8000-2024", "GB 8001-2018"]
    assert rows[0]["status"] == "ACTIVE"
    assert rows[1]["expiry_date"] == "2024-04-30"

    db_session.execute(delete(Standard))
    db_session.commit()
    assert db_session.scalar(select(func.count()).select_from(Standard)) == 0

    imported = import_standards_csv(db_session, csv_path)
    assert imported == 2

    first = db_session.scalar(
        select(Standard).where(Standard.normalized_no == "GB 8000-2024")
    )
    second = db_session.scalar(
        select(Standard).where(Standard.normalized_no == "GB 8001-2018")
    )
    assert first is not None
    assert first.standard_name == "CSV 测试标准 A"
    assert first.status is StandardStatus.ACTIVE
    assert first.effective_date == date(2024, 5, 1)
    assert first.scope == "适用于 CSV 导入测试。"
    assert second is not None
    assert second.status is StandardStatus.REPLACED
    assert second.expiry_date == date(2024, 4, 30)

    assert import_standards_csv(db_session, csv_path) == 2
    assert db_session.scalar(select(func.count()).select_from(Standard)) == 2


def test_ensure_seeds_only_when_table_is_empty(
    db_session: Session,
    tmp_path,
) -> None:
    _seed(db_session)
    csv_path = tmp_path / "standards.csv"
    export_standards_csv(db_session, csv_path)

    db_session.execute(delete(Standard))
    db_session.commit()

    first = ensure_standards_seeded(db_session, csv_path)
    assert first.status == "imported"
    assert first.imported == 2

    second = ensure_standards_seeded(db_session, csv_path)
    assert second.status == "skipped"
    assert second.imported == 0
    assert db_session.scalar(select(func.count()).select_from(Standard)) == 2


def test_missing_csv_is_reported(db_session: Session, tmp_path) -> None:
    result = ensure_standards_seeded(db_session, tmp_path / "missing.csv")
    assert result.status == "missing"


def test_import_rejects_missing_required_columns(
    db_session: Session,
    tmp_path,
) -> None:
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("standard_no,status\nGB 9000-2024,ACTIVE\n", encoding="utf-8")

    try:
        import_standards_csv(db_session, csv_path)
    except ValueError as exc:
        assert "standard_name" in str(exc)
    else:  # pragma: no cover - explicit failure
        raise AssertionError("expected ValueError")
