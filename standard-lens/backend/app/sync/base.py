"""Data-source interfaces for standard synchronization.

Adapters must implement :class:`StandardDataSource`. The sync service only
depends on this interface, so a different public source can be added later
without changing persistence or scheduling code.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime

from app.models.standard import StandardStatus
from app.models.standard_relation import StandardRelationType


class DataSourceError(Exception):
    """A source request or parse failed."""


@dataclass(frozen=True, slots=True)
class StandardListItem:
    """Metadata available from a list/search page."""

    source_id: str
    standard_no: str
    standard_name: str
    status: StandardStatus
    publish_date: date | None
    effective_date: date | None
    standard_type: str | None
    standard_year: int | None
    source_url: str


@dataclass(frozen=True, slots=True)
class StandardRelationData:
    """A replacement/amendment edge as seen from the current standard."""

    target_standard_no: str
    target_standard_name: str | None
    target_source_id: str | None
    target_source_url: str | None
    relation_type: StandardRelationType


@dataclass(frozen=True, slots=True)
class StandardDetailData:
    """Full metadata parsed from a standard detail page."""

    source_id: str
    standard_no: str
    standard_name: str
    status: StandardStatus
    publish_date: date | None
    effective_date: date | None
    expiry_date: date | None
    standard_type: str | None
    standard_year: int | None
    scope: str | None
    source_url: str
    relations: tuple[StandardRelationData, ...] = ()


class StandardDataSource(ABC):
    """Replaceable adapter for a public standard information source."""

    @abstractmethod
    def source_name(self) -> str:
        """Stable source key stored in ``standard.source`` and ``sync_task.source``."""

    @abstractmethod
    def fetch_list(self) -> Iterator[StandardListItem]:
        """Yield all standards (used only for a full initialization)."""

    @abstractmethod
    def fetch_detail(self, item: StandardListItem) -> StandardDetailData:
        """Fetch full metadata and relations for one list item."""

    @abstractmethod
    def fetch_updates(self, since: datetime) -> Iterator[StandardListItem]:
        """Yield standards updated/published at or after ``since``."""

    def close(self) -> None:
        """Release HTTP resources. Adapters without resources may do nothing."""

    def __enter__(self) -> "StandardDataSource":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
