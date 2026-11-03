from datetime import date, datetime
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.models.standard import StandardStatus
from app.models.standard_relation import StandardRelationType
from app.sync.base import DataSourceError, StandardListItem
from app.sync.std_samr import StdSamrDataSource

FIXTURES = Path(__file__).parent / "fixtures"


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "sync_page_size": 2,
        "sync_request_interval_seconds": 0.0,
        "sync_timeout_seconds": 5.0,
        "sync_max_retries": 1,
        "sync_retry_backoff_seconds": 0.0,
        "sync_update_max_pages": 5,
        "sync_user_agent": "TestAgent/1.0",
    }
    values.update(overrides)
    return Settings(**values)


def make_source(handler, **settings_overrides: object):
    settings = make_settings(**settings_overrides)
    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleep_calls: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    source = StdSamrDataSource(settings, client=client, sleep=fake_sleep)
    return source, client, sleep_calls


def list_row(
    source_id: str,
    code: str,
    name: str,
    state: str,
    issue_date: str,
    act_date: str,
) -> dict[str, object]:
    return {
        "id": source_id,
        "C_C_NAME": name,
        "C_STD_CODE": code,
        "STD_NATURE": "强制性",
        "ACT_DATE": act_date,
        "STATE": state,
        "ISSUE_DATE": issue_date,
    }


def make_item(**overrides: object) -> StandardListItem:
    values: dict[str, object] = {
        "source_id": "NEWID",
        "standard_no": "GB 29450-2026",
        "standard_name": "玻璃纤维单位产品能源消耗限额",
        "status": StandardStatus.UPCOMING,
        "publish_date": date(2026, 10, 30),
        "effective_date": date(2027, 11, 1),
        "standard_type": "GB",
        "standard_year": 2026,
        "source_url": "https://std.samr.gov.cn/gb/search/gbDetailed?id=NEWID",
    }
    values.update(overrides)
    return StandardListItem(**values)


def test_fetch_list_parses_rows_and_pagination() -> None:
    requests: list[httpx.Request] = []
    rows = [
        list_row(
            "NEWID",
            "<sacinfo>GB</sacinfo> <sacinfo>29450</sacinfo>-2026",
            "玻璃纤维单位产品能源消耗限额",
            "即将实施",
            "2026-10-30",
            "2027-11-01",
        ),
        list_row(
            "CURID",
            "GB 27608-2011",
            "联合冲剪机  安全要求",
            "现行",
            "2011-12-05",
            "2012-10-01",
        ),
        list_row(
            "OLDID",
            "GB 27607-2011",
            "机械压力机  安全技术要求",
            "废止",
            "2011-12-05",
            "2012-10-01",
        ),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["pageNumber"])
        page_size = int(request.url.params["pageSize"])
        start = (page - 1) * page_size
        return httpx.Response(
            200,
            json={"total": 3, "pageNumber": page, "rows": rows[start : start + page_size]},
        )

    source, client, _ = make_source(handler)
    items = list(source.fetch_list())

    assert len(items) == 3
    assert items[0].standard_no == "GB 29450-2026"
    assert items[0].standard_type == "GB"
    assert items[0].standard_year == 2026
    assert items[0].status == StandardStatus.UPCOMING
    assert items[0].publish_date == date(2026, 10, 30)
    assert items[0].effective_date == date(2027, 11, 1)
    assert "id=NEWID" in items[0].source_url
    assert items[2].status == StandardStatus.ABOLISHED

    assert len(requests) == 2
    assert requests[0].url.params["pageNumber"] == "1"
    assert requests[0].url.params["pageSize"] == "2"
    assert requests[0].headers["accept"] == "application/json"
    client.close()


def test_fetch_updates_stops_after_old_page() -> None:
    requests: list[httpx.Request] = []
    pages = {
        1: [
            list_row("A", "GB 1000-2026", "新标准", "现行", "2026-11-02", "2027-01-01"),
            list_row("B", "GB 1001-2026", "边界标准", "现行", "2026-11-01", "2027-01-01"),
        ],
        2: [
            list_row("C", "GB 1002-2026", "旧标准", "现行", "2026-10-30", "2027-01-01"),
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["pageNumber"])
        return httpx.Response(
            200,
            json={"total": 3, "pageNumber": page, "rows": pages.get(page, [])},
        )

    source, client, _ = make_source(handler)
    items = list(source.fetch_updates(datetime(2026, 11, 1)))

    assert [item.standard_no for item in items] == ["GB 1000-2026", "GB 1001-2026"]
    assert len(requests) == 2
    client.close()


def test_fetch_detail_parses_fields_status_and_replaces_relation() -> None:
    html = (FIXTURES / "std_samr_detail_upcoming.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["id"] == "NEWID"
        return httpx.Response(200, text=html, headers={"Content-Type": "text/html; charset=utf-8"})

    source, client, _ = make_source(handler)
    detail = source.fetch_detail(make_item())

    assert detail.standard_no == "GB 29450-2026"
    assert detail.standard_name == "玻璃纤维单位产品能源消耗限额"
    assert detail.status == StandardStatus.UPCOMING
    assert detail.publish_date == date(2026, 10, 30)
    assert detail.effective_date == date(2027, 11, 1)
    assert detail.expiry_date is None
    assert detail.standard_type == "GB"
    assert detail.standard_year == 2026
    assert detail.source_url.endswith("id=NEWID")
    assert len(detail.relations) == 1
    relation = detail.relations[0]
    assert relation.target_standard_no == "GB 29450-2012"
    assert relation.target_source_id == "OLDRUBBER2012"
    assert relation.target_standard_name == "玻璃纤维单位产品能源消耗限额"
    assert relation.relation_type == StandardRelationType.REPLACES
    client.close()


def test_fetch_detail_marks_abolished_with_successor_as_replaced() -> None:
    html = (FIXTURES / "std_samr_detail_abolished.html").read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"Content-Type": "text/html; charset=utf-8"})

    source, client, _ = make_source(handler)
    item = make_item(
        source_id="OLDID",
        standard_no="GB 27607-2011",
        standard_name="机械压力机 安全技术要求",
        status=StandardStatus.ABOLISHED,
        publish_date=date(2011, 12, 5),
        effective_date=date(2012, 10, 1),
        standard_type="GB",
        standard_year=2011,
        source_url="https://std.samr.gov.cn/gb/search/gbDetailed?id=OLDID",
    )
    detail = source.fetch_detail(item)

    assert detail.status == StandardStatus.REPLACED
    assert detail.expiry_date == date(2026, 5, 1)
    assert detail.relations[0].target_standard_no == "GB 17120-2025"
    assert detail.relations[0].relation_type == StandardRelationType.REPLACED_BY
    client.close()


def test_retry_succeeds_after_transient_failure() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"total": 0, "pageNumber": 1, "rows": []})

    source, client, sleep_calls = make_source(handler, sync_max_retries=2)
    assert list(source.fetch_list()) == []
    assert attempts == 3
    assert len(sleep_calls) == 2
    client.close()


def test_retry_exhaustion_raises_data_source_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    source, client, _ = make_source(handler, sync_max_retries=1)
    with pytest.raises(DataSourceError):
        list(source.fetch_list())
    assert attempts == 2
    client.close()


def test_request_rate_limit_uses_sleep() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["pageNumber"])
        rows = (
            [
                list_row("A", "GB 1000-2026", "A", "现行", "2026-11-02", "2027-01-01"),
                list_row("B", "GB 1001-2026", "B", "现行", "2026-11-02", "2027-01-01"),
            ]
            if page == 1
            else [list_row("C", "GB 1002-2026", "C", "现行", "2026-11-02", "2027-01-01")]
        )
        return httpx.Response(200, json={"total": 3, "pageNumber": page, "rows": rows})

    source, client, sleep_calls = make_source(handler, sync_request_interval_seconds=10.0)
    assert len(list(source.fetch_list())) == 3
    assert sleep_calls and sleep_calls[0] > 0
    client.close()


def test_owned_client_has_timeout_and_user_agent() -> None:
    source = StdSamrDataSource(
        make_settings(sync_timeout_seconds=7.0, sync_user_agent="TestAgent/1.0")
    )
    try:
        assert source._client.timeout.read == 7.0
        assert source._client.headers["user-agent"] == "TestAgent/1.0"
    finally:
        source.close()
