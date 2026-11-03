import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.standard import Standard, StandardStatus
from tests.factories import make_standard


def test_normalized_no_is_unique(db_session: Session) -> None:
    db_session.add(make_standard(standard_no="GB 4806.11-2023"))
    db_session.add(make_standard(standard_no="gb4806.11—2023"))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    count = db_session.scalar(select(func.count()).select_from(Standard))
    assert count == 0


def test_status_defaults_to_unknown(db_session: Session) -> None:
    standard = Standard(
        standard_no="GB 1234-2020",
        normalized_no="GB 1234-2020",
        standard_name="测试标准",
    )
    db_session.add(standard)
    db_session.commit()
    db_session.refresh(standard)

    assert standard.status == StandardStatus.UNKNOWN
