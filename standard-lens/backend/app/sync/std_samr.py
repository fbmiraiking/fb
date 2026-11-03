import logging
import random
import re
import time
from collections.abc import Callable, Iterator
from datetime import date, datetime
from urllib.parse import parse_qs, quote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import Settings, get_settings
from app.models.standard import StandardStatus
from app.models.standard_relation import StandardRelationType
from app.sync.base import (
    DataSourceError,
    StandardDataSource,
    StandardDetailData,
    StandardListItem,
    StandardRelationData,
)

logger = logging.getLogger(__name__)

_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_TYPE_RE = re.compile(r"^([A-Z]+(?:/[A-Z]+)?)")
_YEAR_RE = re.compile(r"[-:](\d{4})\s*$")


class _RetryableHTTPError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class StdSamrDataSource(StandardDataSource):
    """Adapter for 全国标准信息公共服务平台 (std.samr.gov.cn).

    The source exposes a JSON list endpoint and HTML detail pages. This adapter
    never downloads PDFs; it stores metadata and the official detail URL only.

    ``fetch_list`` is used for a full initialization. ``fetch_updates`` walks
    the list in its default issue-date-descending order and stops once a page
    is older than the requested cutoff.
    """

    SOURCE_NAME = "std_samr"
    BASE_URL = "https://std.samr.gov.cn"
    LIST_PATH = "/gb/search/gbQueryPage"
    DETAIL_PATH = "/gb/search/gbDetailed"
    RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

    STATUS_MAP: dict[str, StandardStatus] = {
        "现行": StandardStatus.ACTIVE,
        "即将实施": StandardStatus.UPCOMING,
        "废止": StandardStatus.ABOLISHED,
        "已废止": StandardStatus.ABOLISHED,
        "被代替": StandardStatus.REPLACED,
        "被替代": StandardStatus.REPLACED,
        "被废止": StandardStatus.ABOLISHED,
    }

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self._page_size = max(1, min(50, self.settings.sync_page_size))
        self._max_retries = max(0, self.settings.sync_max_retries)
        self._retry_backoff = max(0.0, self.settings.sync_retry_backoff_seconds)
        self._request_interval = max(0.0, self.settings.sync_request_interval_seconds)
        self._max_update_pages = max(1, self.settings.sync_update_max_pages)
        self._sleep = sleep
        self._last_request_at: float | None = None
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(self.settings.sync_timeout_seconds),
            follow_redirects=True,
            headers={"User-Agent": self.settings.sync_user_agent},
        )

    def source_name(self) -> str:
        return self.SOURCE_NAME

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------ HTTP

    def _throttle(self) -> None:
        if self._request_interval <= 0:
            return
        now = time.monotonic()
        if self._last_request_at is not None:
            wait = self._request_interval - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
        self._last_request_at = time.monotonic()

    def _request(
        self,
        url: str,
        *,
        params: dict[str, object] | None = None,
        accept: str,
    ) -> httpx.Response:
        target = urlparse(url)
        base = urlparse(self.BASE_URL)
        if target.scheme not in ("http", "https") or target.netloc != base.netloc:
            raise DataSourceError(f"拒绝访问非数据源地址: {url}")

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                response = self._client.get(
                    url,
                    params=params,
                    headers={"Accept": accept},
                )
                if response.status_code in self.RETRYABLE_STATUSES:
                    raise _RetryableHTTPError(response.status_code)
                response.raise_for_status()
                return response
            except (httpx.TimeoutException, httpx.TransportError, _RetryableHTTPError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                delay = self._retry_backoff * (2**attempt) + random.uniform(0, 0.2)
                logger.warning(
                    "std_samr request failed (%s), retry %d/%d in %.2fs",
                    exc,
                    attempt + 1,
                    self._max_retries,
                    delay,
                )
                self._sleep(delay)
            except httpx.HTTPStatusError as exc:
                raise DataSourceError(
                    f"std_samr 返回 HTTP {exc.response.status_code}: {url}"
                ) from exc

        raise DataSourceError(f"std_samr 请求失败（已重试）: {url}: {last_error}")

    def _get_list_page(self, page: int) -> dict[str, object]:
        response = self._request(
            f"{self.BASE_URL}{self.LIST_PATH}",
            params={"pageNumber": page, "pageSize": self._page_size},
            accept="application/json",
        )
        try:
            data = response.json()
        except ValueError as exc:
            raise DataSourceError("std_samr 列表接口返回了非 JSON 内容") from exc
        if not isinstance(data, dict):
            raise DataSourceError("std_samr 列表接口返回格式不正确")
        return data

    # --------------------------------------------------------------- listing

    def fetch_list(self) -> Iterator[StandardListItem]:
        page = 1
        while True:
            data = self._get_list_page(page)
            rows = data.get("rows")
            if not isinstance(rows, list) or not rows:
                break

            for row in rows:
                item = self._parse_list_row(row)
                if item is not None:
                    yield item

            total = data.get("total")
            if isinstance(total, int) and page * self._page_size >= total:
                break
            if len(rows) < self._page_size:
                break
            page += 1

    def fetch_updates(self, since: datetime) -> Iterator[StandardListItem]:
        since_date = since.date()
        for page in range(1, self._max_update_pages + 1):
            data = self._get_list_page(page)
            rows = data.get("rows")
            if not isinstance(rows, list) or not rows:
                break

            page_dates: list[date] = []
            for row in rows:
                item = self._parse_list_row(row)
                if item is None:
                    continue
                if item.publish_date is not None:
                    page_dates.append(item.publish_date)
                    if item.publish_date >= since_date:
                        yield item

            # The public list is ordered by issue date descending. Once an
            # entire page is older than the cutoff, later pages are older too.
            if page_dates and max(page_dates) < since_date:
                break
            if len(rows) < self._page_size:
                break

    def _parse_list_row(self, row: object) -> StandardListItem | None:
        if not isinstance(row, dict):
            return None

        source_id = str(row.get("id") or "").strip()
        standard_no = self._clean_standard_no(row.get("C_STD_CODE"))
        standard_name = self._clean_text(row.get("C_C_NAME"))
        if not source_id or not standard_no or not standard_name:
            return None

        status_text = self._clean_text(row.get("STATE"))
        status = self.STATUS_MAP.get(status_text, StandardStatus.UNKNOWN)
        publish_date = self._parse_date(row.get("ISSUE_DATE"))
        effective_date = self._parse_date(row.get("ACT_DATE"))
        standard_type = self._parse_type(standard_no) or self._clean_text(
            row.get("STD_NATURE")
        ) or None
        standard_year = self._parse_year(standard_no) or (
            publish_date.year if publish_date is not None else None
        )

        return StandardListItem(
            source_id=source_id,
            standard_no=standard_no,
            standard_name=standard_name,
            status=status,
            publish_date=publish_date,
            effective_date=effective_date,
            standard_type=standard_type,
            standard_year=standard_year,
            source_url=self._detail_url(source_id),
        )

    # ---------------------------------------------------------------- detail

    def fetch_detail(self, item: StandardListItem) -> StandardDetailData:
        url = item.source_url or self._detail_url(item.source_id)
        response = self._request(url, accept="text/html")
        soup = BeautifulSoup(response.text, "html.parser")

        base_info = self._parse_base_info(soup)
        relations = self._parse_relations(soup)
        standard_no = self._clean_standard_no(base_info.get("标准号")) or item.standard_no
        standard_name = self._clean_text(soup.select_one(".page-header h4")) or item.standard_name
        publish_date = self._parse_date(base_info.get("发布日期")) or item.publish_date
        effective_date = self._parse_date(base_info.get("实施日期")) or item.effective_date
        expiry_date = self._parse_date(base_info.get("废止日期"))
        standard_type = self._parse_type(standard_no) or item.standard_type
        standard_year = self._parse_year(standard_no) or (
            publish_date.year if publish_date is not None else item.standard_year
        )

        status = self._parse_detail_status(soup)
        if status is None:
            status = item.status
        if status in (StandardStatus.ABOLISHED, StandardStatus.UNKNOWN) and any(
            relation.relation_type == StandardRelationType.REPLACED_BY
            for relation in relations
        ):
            status = StandardStatus.REPLACED

        return StandardDetailData(
            source_id=item.source_id,
            standard_no=standard_no,
            standard_name=standard_name,
            status=status,
            publish_date=publish_date,
            effective_date=effective_date,
            expiry_date=expiry_date,
            standard_type=standard_type,
            standard_year=standard_year,
            scope=None,
            source_url=url,
            relations=tuple(relations),
        )

    def _parse_base_info(self, soup: BeautifulSoup) -> dict[str, str]:
        info: dict[str, str] = {}
        for name_node in soup.select("dt.basicInfo-item.name"):
            value_node = name_node.find_next_sibling("dd")
            if value_node is None:
                continue
            key = self._clean_text(name_node)
            value = self._clean_text(value_node)
            if key:
                info[key] = value
        return info

    def _parse_detail_status(self, soup: BeautifulSoup) -> StandardStatus | None:
        for node in soup.select(".page-header .s-status"):
            status = self.STATUS_MAP.get(self._clean_text(node))
            if status is not None:
                return status
        return None

    def _parse_relations(self, soup: BeautifulSoup) -> list[StandardRelationData]:
        relations: list[StandardRelationData] = []
        seen: set[tuple[str, StandardRelationType]] = set()

        groups = (
            ("div.replDiv", StandardRelationType.REPLACES),
            ("div.repledDiv", StandardRelationType.REPLACED_BY),
        )
        for selector, relation_type in groups:
            for container in soup.select(selector):
                anchor = container.find("a", href=True)
                if anchor is None:
                    continue
                target_no = self._clean_standard_no(anchor.get_text(" ", strip=True))
                if not target_no:
                    continue

                target_url = self._absolute_url(anchor.get("href", ""))
                name_node = container.find("div", class_="replA")
                target_name = self._clean_text(name_node) if name_node is not None else None
                key = (target_no, relation_type)
                if key in seen:
                    continue
                seen.add(key)
                relations.append(
                    StandardRelationData(
                        target_standard_no=target_no,
                        target_standard_name=target_name or None,
                        target_source_id=self._source_id_from_url(target_url),
                        target_source_url=target_url,
                        relation_type=relation_type,
                    )
                )
        return relations

    # --------------------------------------------------------------- helpers

    @classmethod
    def _map_status_text(cls, text: str) -> StandardStatus | None:
        return cls.STATUS_MAP.get(text.strip())

    @staticmethod
    def _clean_text(value: object) -> str:
        if value is None:
            return ""
        soup = BeautifulSoup(str(value), "html.parser")
        text = soup.get_text(" ")
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _clean_standard_no(cls, value: object) -> str:
        text = cls._clean_text(value)
        text = re.sub(r"\s*-\s*", "-", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _parse_date(value: object) -> date | None:
        if value is None:
            return None
        match = _DATE_RE.search(str(value))
        if match is None:
            return None
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    @staticmethod
    def _parse_type(standard_no: str) -> str | None:
        match = _TYPE_RE.match(standard_no.upper())
        return match.group(1) if match is not None else None

    @staticmethod
    def _parse_year(standard_no: str) -> int | None:
        match = _YEAR_RE.search(standard_no)
        return int(match.group(1)) if match is not None else None

    def _detail_url(self, source_id: str) -> str:
        return f"{self.BASE_URL}{self.DETAIL_PATH}?id={quote(source_id, safe='')}"

    def _absolute_url(self, href: str) -> str | None:
        if not href:
            return None
        if href.startswith("http://") or href.startswith("https://"):
            return href
        if href.startswith("/"):
            return f"{self.BASE_URL}{href}"
        return None

    @staticmethod
    def _source_id_from_url(url: str | None) -> str | None:
        if not url:
            return None
        parsed = urlparse(url)
        ids = parse_qs(parsed.query).get("id")
        return ids[0] if ids else None
