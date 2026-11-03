import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import make_standard


@pytest.mark.parametrize(
    "query",
    [
        "GB 4806.11-2023",
        "gb4806.11-2023",
        "GB 4806.11—2023",
        " GB4806.11 - 2023 ",
    ],
)
def test_search_by_standard_number_variants(
    client: TestClient,
    db_session: Session,
    query: str,
) -> None:
    standard = make_standard(standard_no="GB4806.11-2023")
    db_session.add(standard)
    db_session.commit()

    response = client.get("/api/v1/standards/search", params={"q": query})

    assert response.status_code == 200
    body = response.json()
    assert body["normalized_query"] == "GB 4806.11-2023"
    assert body["total"] == 1
    assert body["items"][0]["id"] == standard.id
    assert body["items"][0]["standard_no"] == "GB4806.11-2023"


def test_search_by_name_fuzzy(client: TestClient, db_session: Session) -> None:
    rubber = make_standard()
    guideline = make_standard(
        standard_no="GB/T 1.1-2020",
        standard_name="标准化工作导则 第1部分：标准化文件的结构和起草规则",
        standard_type="GB/T",
        standard_year=2020,
    )
    db_session.add_all([rubber, guideline])
    db_session.commit()

    response = client.get("/api/v1/standards/search", params={"q": "橡胶"})

    assert response.status_code == 200
    body = response.json()
    assert body["normalized_query"] is None
    assert body["total"] == 1
    assert body["items"][0]["id"] == rubber.id
    assert "scope" not in body["items"][0]


def test_search_matches_raw_standard_no_when_normalized_key_differs(
    client: TestClient,
    db_session: Session,
) -> None:
    standard = make_standard(standard_no="GB 9999-2020", normalized_no="LEGACY-KEY")
    db_session.add(standard)
    db_session.commit()

    response = client.get("/api/v1/standards/search", params={"q": "GB 9999-2020"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.parametrize("query", ["%", "_", "!"])
def test_search_escapes_like_wildcards(
    client: TestClient,
    db_session: Session,
    query: str,
) -> None:
    db_session.add(make_standard())
    db_session.commit()

    response = client.get("/api/v1/standards/search", params={"q": query})

    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_search_blank_query_returns_empty_result(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add(make_standard())
    db_session.commit()

    response = client.get("/api/v1/standards/search", params={"q": "   "})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_search_total_is_independent_of_pagination(
    client: TestClient,
    db_session: Session,
) -> None:
    db_session.add_all(
        [
            make_standard(),
            make_standard(
                standard_no="GB 4806.7-2023",
                standard_name="食品安全国家标准 食品接触用塑料材料及制品",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        "/api/v1/standards/search",
        params={"q": "食品", "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["limit"] == 1
    assert body["offset"] == 0


def test_exact_number_match_is_sorted_first(
    client: TestClient,
    db_session: Session,
) -> None:
    exact = make_standard(standard_no="GB 4806.11-2023", standard_name="橡胶材料标准")
    name_only = make_standard(
        standard_no="GB 9999-2023",
        standard_name="引用 GB 4806.11-2023 的说明",
    )
    db_session.add_all([exact, name_only])
    db_session.commit()

    response = client.get(
        "/api/v1/standards/search",
        params={"q": "GB 4806.11-2023"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["id"] == exact.id


def test_standard_detail(client: TestClient, db_session: Session) -> None:
    standard = make_standard()
    db_session.add(standard)
    db_session.commit()

    response = client.get(f"/api/v1/standards/{standard.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == standard.id
    assert body["standard_no"] == "GB 4806.11-2023"
    assert body["normalized_no"] == "GB 4806.11-2023"
    assert body["standard_name"] == "食品安全国家标准 食品接触用橡胶材料及制品"
    assert body["status"] == "ACTIVE"
    assert body["publish_date"] == "2023-09-06"
    assert body["effective_date"] == "2024-04-01"
    assert body["expiry_date"] is None
    assert body["standard_year"] == 2023
    assert body["scope"] == "适用于食品接触用橡胶材料及制品。"
    assert body["source"] == "openstd"
    assert body["source_url"].startswith("https://openstd.samr.gov.cn/")
    assert "created_at" in body
    assert "updated_at" in body


def test_standard_detail_not_found(client: TestClient) -> None:
    response = client.get("/api/v1/standards/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "标准不存在"}
