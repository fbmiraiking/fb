from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelationType
from tests.factories import make_relation, make_standard


def _add_version_chain(
    db_session: Session,
) -> tuple[Standard, Standard, Standard]:
    old = make_standard(
        standard_no="GB 4806.11-2018",
        standard_name="食品接触用橡胶材料及制品（2018）",
        status=StandardStatus.REPLACED,
        standard_year=2018,
        publish_date=date(2018, 1, 1),
        effective_date=date(2018, 7, 1),
        expiry_date=date(2024, 4, 30),
    )
    current = make_standard(
        standard_no="GB 4806.11-2024",
        standard_name="食品接触用橡胶材料及制品（2024）",
        status=StandardStatus.ACTIVE,
        standard_year=2024,
        publish_date=date(2024, 1, 1),
        effective_date=date(2024, 5, 1),
    )
    upcoming = make_standard(
        standard_no="GB 4806.11-2027",
        standard_name="食品接触用橡胶材料及制品（2027）",
        status=StandardStatus.UPCOMING,
        standard_year=2027,
        publish_date=date(2027, 1, 1),
        effective_date=date(2027, 7, 1),
    )
    db_session.add_all([old, current, upcoming])
    db_session.commit()

    db_session.add_all(
        [
            make_relation(current.id, old.id, StandardRelationType.REPLACES),
            make_relation(upcoming.id, current.id, StandardRelationType.REPLACES),
        ]
    )
    db_session.commit()
    return old, current, upcoming


def test_version_chain_order_flags_and_camel_case(
    client: TestClient,
    db_session: Session,
) -> None:
    _, current, _ = _add_version_chain(db_session)

    response = client.get(f"/api/v1/standards/{current.id}/versions")

    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert [item["standardNo"] for item in items] == [
        "GB 4806.11-2027",
        "GB 4806.11-2024",
        "GB 4806.11-2018",
    ]
    assert [item["standardYear"] for item in items] == [2027, 2024, 2018]

    assert set(items[0]) == {
        "id",
        "standardNo",
        "standardName",
        "status",
        "publishDate",
        "effectiveDate",
        "expiryDate",
        "standardYear",
        "isHistorical",
        "isCurrent",
        "isUpcoming",
    }

    by_number = {item["standardNo"]: item for item in items}
    assert by_number["GB 4806.11-2027"]["status"] == "UPCOMING"
    assert by_number["GB 4806.11-2027"]["isUpcoming"] is True
    assert by_number["GB 4806.11-2027"]["isCurrent"] is False
    assert by_number["GB 4806.11-2027"]["isHistorical"] is False

    assert by_number["GB 4806.11-2024"]["status"] == "ACTIVE"
    assert by_number["GB 4806.11-2024"]["isCurrent"] is True
    assert by_number["GB 4806.11-2024"]["isUpcoming"] is False
    assert by_number["GB 4806.11-2024"]["isHistorical"] is False

    assert by_number["GB 4806.11-2018"]["status"] == "REPLACED"
    assert by_number["GB 4806.11-2018"]["isHistorical"] is True
    assert by_number["GB 4806.11-2018"]["isCurrent"] is False
    assert by_number["GB 4806.11-2018"]["expiryDate"] == "2024-04-30"

    assert all("effectiveDate" in item for item in items)
    assert by_number["GB 4806.11-2018"]["effectiveDate"] == "2018-07-01"
    assert "standard_no" not in items[0]


def test_version_chain_can_start_from_oldest_standard(
    client: TestClient,
    db_session: Session,
) -> None:
    old, _, _ = _add_version_chain(db_session)

    response = client.get(f"/api/v1/standards/{old.id}/versions")

    assert response.status_code == 200
    assert [item["standardYear"] for item in response.json()] == [2027, 2024, 2018]


def test_newest_year_is_not_automatically_current(
    client: TestClient,
    db_session: Session,
) -> None:
    current = make_standard(
        standard_no="GB 1111-2024",
        standard_name="现行版本",
        status=StandardStatus.ACTIVE,
        standard_year=2024,
        publish_date=date(2024, 1, 1),
        effective_date=date(2024, 5, 1),
    )
    newer_but_abolished = make_standard(
        standard_no="GB 1111-2030",
        standard_name="已废止但年份更大的版本",
        status=StandardStatus.ABOLISHED,
        standard_year=2030,
        publish_date=date(2030, 1, 1),
        effective_date=date(2030, 6, 1),
        expiry_date=date(2031, 1, 1),
    )
    db_session.add_all([current, newer_but_abolished])
    db_session.commit()
    db_session.add(
        make_relation(
            newer_but_abolished.id,
            current.id,
            StandardRelationType.AMENDS,
        )
    )
    db_session.commit()

    response = client.get(f"/api/v1/standards/{current.id}/versions")

    assert response.status_code == 200
    items = response.json()
    assert items[0]["standardYear"] == 2030
    assert items[0]["isHistorical"] is True
    assert items[0]["isCurrent"] is False
    assert items[1]["standardNo"] == "GB 1111-2024"
    assert items[1]["isCurrent"] is True


def test_version_chain_includes_amendments_but_excludes_related(
    client: TestClient,
    db_session: Session,
) -> None:
    base = make_standard(
        standard_no="GB 2222-2018",
        standard_name="基础版本",
        status=StandardStatus.REPLACED,
        standard_year=2018,
        effective_date=date(2018, 1, 1),
    )
    amended = make_standard(
        standard_no="GB 2222-2020",
        standard_name="修改版本",
        status=StandardStatus.ACTIVE,
        standard_year=2020,
        effective_date=date(2020, 1, 1),
    )
    successor = make_standard(
        standard_no="GB 2222-2024",
        standard_name="后续版本",
        status=StandardStatus.UPCOMING,
        standard_year=2024,
        effective_date=date(2024, 1, 1),
    )
    related = make_standard(
        standard_no="GB 9999-2021",
        standard_name="仅关联标准",
        status=StandardStatus.ACTIVE,
        standard_year=2021,
        effective_date=date(2021, 1, 1),
    )
    db_session.add_all([base, amended, successor, related])
    db_session.commit()
    db_session.add_all(
        [
            make_relation(amended.id, base.id, StandardRelationType.AMENDS),
            make_relation(amended.id, successor.id, StandardRelationType.REPLACED_BY),
            make_relation(base.id, related.id, StandardRelationType.RELATED),
        ]
    )
    db_session.commit()

    response = client.get(f"/api/v1/standards/{amended.id}/versions")

    assert response.status_code == 200
    items = response.json()
    assert [item["standardNo"] for item in items] == [
        "GB 2222-2024",
        "GB 2222-2020",
        "GB 2222-2018",
    ]
    assert related.id not in {item["id"] for item in items}


def test_version_chain_without_relations_returns_itself(
    client: TestClient,
    db_session: Session,
) -> None:
    standard = make_standard(
        standard_no="GB 3333-2024",
        status=StandardStatus.UNKNOWN,
        standard_year=2024,
        effective_date=None,
        publish_date=None,
    )
    db_session.add(standard)
    db_session.commit()

    response = client.get(f"/api/v1/standards/{standard.id}/versions")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == standard.id
    assert items[0]["effectiveDate"] is None
    assert items[0]["isHistorical"] is False
    assert items[0]["isCurrent"] is False
    assert items[0]["isUpcoming"] is False


def test_version_chain_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/standards/999999/versions")

    assert response.status_code == 404
    assert response.json() == {"detail": "标准不存在"}


def test_version_chain_falls_back_to_effective_date_year(
    client: TestClient,
    db_session: Session,
) -> None:
    old = make_standard(
        standard_no="GB 4444-2019",
        status=StandardStatus.REPLACED,
        standard_year=None,
        effective_date=date(2019, 3, 1),
    )
    current = make_standard(
        standard_no="GB 4444-2024",
        status=StandardStatus.ACTIVE,
        standard_year=None,
        effective_date=date(2024, 6, 1),
    )
    db_session.add_all([old, current])
    db_session.commit()
    db_session.add(make_relation(current.id, old.id, StandardRelationType.REPLACES))
    db_session.commit()

    response = client.get(f"/api/v1/standards/{current.id}/versions")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [current.id, old.id]


def test_version_chain_same_year_uses_effective_date(
    client: TestClient,
    db_session: Session,
) -> None:
    early = make_standard(
        standard_no="GB 5555.1-2024",
        status=StandardStatus.REPLACED,
        standard_year=2024,
        effective_date=date(2024, 1, 1),
    )
    late = make_standard(
        standard_no="GB 5555.2-2024",
        status=StandardStatus.ACTIVE,
        standard_year=2024,
        effective_date=date(2024, 6, 1),
    )
    db_session.add_all([early, late])
    db_session.commit()
    db_session.add(make_relation(late.id, early.id, StandardRelationType.REPLACES))
    db_session.commit()

    response = client.get(f"/api/v1/standards/{late.id}/versions")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [late.id, early.id]


def test_relation_rejects_duplicate_edge(db_session: Session) -> None:
    first = make_standard(standard_no="GB 6666-2020", standard_year=2020)
    second = make_standard(standard_no="GB 6666-2024", standard_year=2024)
    db_session.add_all([first, second])
    db_session.commit()

    db_session.add(make_relation(second.id, first.id))
    db_session.add(make_relation(second.id, first.id))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_relation_rejects_self_edge(db_session: Session) -> None:
    standard = make_standard(standard_no="GB 7777-2024", standard_year=2024)
    db_session.add(standard)
    db_session.commit()

    db_session.add(make_relation(standard.id, standard.id))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
