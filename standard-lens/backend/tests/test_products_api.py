from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.product import (
    ReviewStatus,
    StandardProductRelationType,
)
from app.models.standard import StandardStatus
from tests.factories import make_category, make_product_relation, make_standard


def _standard(
    standard_no: str,
    name: str,
    status: StandardStatus,
    effective: date,
    expiry: date | None = None,
):
    return make_standard(
        standard_no=standard_no,
        standard_name=name,
        status=status,
        standard_year=effective.year,
        publish_date=date(effective.year, 1, 1),
        effective_date=effective,
        expiry_date=expiry,
    )


def test_product_search_by_name_and_alias(client: TestClient, db_session: Session) -> None:
    bottle = make_category(
        "奶瓶",
        "婴幼儿喂养用品",
        aliases=("婴儿奶瓶", "feeding bottle"),
    )
    container = make_category("塑料容器", aliases=("塑料瓶",))
    db_session.add_all([bottle, container])
    db_session.commit()

    response = client.get("/api/v1/products/search", params={"q": "奶瓶"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert set(item) == {"id", "name", "description", "parentId", "aliases"}
    assert item["id"] == bottle.id
    assert item["name"] == "奶瓶"
    assert item["aliases"] == ["feeding bottle", "婴儿奶瓶"]
    assert item["parentId"] is None

    for query in ("婴儿", "FEEDING"):
        response = client.get("/api/v1/products/search", params={"q": query})
        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == bottle.id

    response = client.get("/api/v1/products/search", params={"q": "塑料"})
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == container.id


def test_product_search_wildcards_and_blank(client: TestClient, db_session: Session) -> None:
    db_session.add(make_category("奶瓶", aliases=("婴儿奶瓶",)))
    db_session.commit()

    assert (
        client.get("/api/v1/products/search", params={"q": "%"}).json()["total"] == 0
    )
    assert (
        client.get("/api/v1/products/search", params={"q": "   "}).json()["total"] == 0
    )


def test_product_search_pagination(client: TestClient, db_session: Session) -> None:
    db_session.add_all(
        [
            make_category("奶瓶", aliases=("婴儿奶瓶",)),
            make_category("奶瓶刷", aliases=("奶瓶清洗刷",)),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/products/search",
        params={"q": "奶瓶", "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_product_standards_groups_sort_and_deduplicates(
    client: TestClient,
    db_session: Session,
) -> None:
    category = make_category(
        "奶瓶",
        "婴幼儿喂养用品",
        aliases=("婴儿奶瓶",),
    )
    standards = {
        "pending": _standard(
            "GB 9000-2024",
            "待审核安全标准",
            StandardStatus.ACTIVE,
            date(2024, 6, 1),
        ),
        "direct": _standard(
            "GB 8000-2024",
            "直接适用标准",
            StandardStatus.ACTIVE,
            date(2024, 5, 1),
        ),
        "multi": _standard(
            "GB 7000-2023",
            "多关系标准",
            StandardStatus.ACTIVE,
            date(2023, 1, 1),
        ),
        "material": _standard(
            "GB 6000-2020",
            "材料标准",
            StandardStatus.ACTIVE,
            date(2020, 1, 1),
        ),
        "upcoming": _standard(
            "GB 5000-2027",
            "即将实施标准",
            StandardStatus.UPCOMING,
            date(2027, 7, 1),
        ),
        "historical": _standard(
            "GB 4000-2018",
            "历史版本",
            StandardStatus.REPLACED,
            date(2018, 7, 1),
            expiry=date(2024, 4, 30),
        ),
        "abolished": _standard(
            "GB 3000-2010",
            "已废止标准",
            StandardStatus.ABOLISHED,
            date(2010, 1, 1),
        ),
        "possible": _standard(
            "GB 2000-2025",
            "可能相关标准",
            StandardStatus.ACTIVE,
            date(2025, 1, 1),
        ),
        "unknown": _standard(
            "GB 1000-2020",
            "状态未知标准",
            StandardStatus.UNKNOWN,
            date(2020, 6, 1),
        ),
        "rejected": _standard(
            "GB 1100-2024",
            "已驳回标准",
            StandardStatus.ACTIVE,
            date(2024, 1, 1),
        ),
    }
    db_session.add(category)
    db_session.add_all(standards.values())
    db_session.commit()

    relations = [
        make_product_relation(
            standards["pending"].id,
            category.id,
            StandardProductRelationType.SAFETY,
            confidence=Decimal("0.9000"),
            review_status=ReviewStatus.PENDING,
        ),
        make_product_relation(
            standards["direct"].id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
        ),
        make_product_relation(
            standards["multi"].id,
            category.id,
            StandardProductRelationType.SAFETY,
            confidence=Decimal("1.0000"),
        ),
        make_product_relation(
            standards["multi"].id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
            confidence=Decimal("0.8000"),
        ),
        make_product_relation(
            standards["material"].id,
            category.id,
            StandardProductRelationType.MATERIAL,
        ),
        make_product_relation(
            standards["upcoming"].id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
        ),
        make_product_relation(
            standards["historical"].id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
        ),
        make_product_relation(
            standards["abolished"].id,
            category.id,
            StandardProductRelationType.SAFETY,
        ),
        make_product_relation(
            standards["possible"].id,
            category.id,
            StandardProductRelationType.POSSIBLE,
            confidence=Decimal("0.4000"),
        ),
        make_product_relation(
            standards["unknown"].id,
            category.id,
            StandardProductRelationType.GENERAL,
        ),
        make_product_relation(
            standards["rejected"].id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
            review_status=ReviewStatus.REJECTED,
        ),
    ]
    db_session.add_all(relations)
    db_session.commit()

    response = client.get(f"/api/v1/products/{category.id}/standards")

    assert response.status_code == 200
    body = response.json()
    assert body["product"]["name"] == "奶瓶"
    assert body["product"]["aliases"] == ["婴儿奶瓶"]
    assert set(body) == {"product", "current", "upcoming", "historical", "related"}

    assert [item["standardNo"] for item in body["current"]] == [
        "GB 9000-2024",
        "GB 8000-2024",
        "GB 7000-2023",
        "GB 6000-2020",
    ]
    assert [item["standardNo"] for item in body["upcoming"]] == ["GB 5000-2027"]
    assert [item["standardNo"] for item in body["historical"]] == [
        "GB 4000-2018",
        "GB 3000-2010",
    ]
    assert [item["standardNo"] for item in body["related"]] == [
        "GB 2000-2025",
        "GB 1000-2020",
    ]

    expected_keys = {
        "id",
        "standardNo",
        "standardName",
        "status",
        "effectiveDate",
        "expiryDate",
        "relationType",
        "reviewStatus",
    }
    assert set(body["current"][0]) == expected_keys

    by_no = {
        item["standardNo"]: item
        for group in ("current", "upcoming", "historical", "related")
        for item in body[group]
    }
    assert by_no["GB 9000-2024"]["reviewStatus"] == "PENDING"
    assert by_no["GB 8000-2024"]["reviewStatus"] == "APPROVED"
    assert by_no["GB 7000-2023"]["relationType"] == "DIRECT_APPLICABLE"
    assert by_no["GB 2000-2025"]["relationType"] == "POSSIBLE"
    assert by_no["GB 1000-2020"]["relationType"] == "GENERAL"
    assert by_no["GB 4000-2018"]["expiryDate"] == "2024-04-30"
    assert by_no["GB 4000-2018"]["status"] == "REPLACED"
    assert "GB 1100-2024" not in by_no


def test_product_standards_without_relations(
    client: TestClient,
    db_session: Session,
) -> None:
    category = make_category("空分类")
    db_session.add(category)
    db_session.commit()

    response = client.get(f"/api/v1/products/{category.id}/standards")

    assert response.status_code == 200
    body = response.json()
    assert body["current"] == []
    assert body["upcoming"] == []
    assert body["historical"] == []
    assert body["related"] == []
    assert body["product"]["aliases"] == []


def test_product_standards_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/products/999999/standards")

    assert response.status_code == 404
    assert response.json() == {"detail": "商品分类不存在"}
