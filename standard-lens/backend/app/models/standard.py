import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StandardStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    REPLACED = "REPLACED"
    ABOLISHED = "ABOLISHED"
    UNKNOWN = "UNKNOWN"


class Standard(Base):
    """A product standard and its lifecycle metadata.

    ``normalized_no`` is the canonical form produced by
    :class:`app.utils.standard_no.StandardNoNormalizer` and is unique.
    """

    __tablename__ = "standard"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standard_no: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    normalized_no: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )
    standard_name: Mapped[str] = mapped_column(String(512), nullable=False)
    standard_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[StandardStatus] = mapped_column(
        Enum(
            StandardStatus,
            name="standard_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=StandardStatus.UNKNOWN,
        server_default=StandardStatus.UNKNOWN.value,
    )
    publish_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    standard_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Standard id={self.id} no={self.standard_no!r} status={self.status!r}>"

    @property
    def is_current(self) -> bool:
        return self.status == StandardStatus.ACTIVE

    @property
    def is_upcoming(self) -> bool:
        return self.status == StandardStatus.UPCOMING

    @property
    def is_historical(self) -> bool:
        return self.status in (StandardStatus.REPLACED, StandardStatus.ABOLISHED)
