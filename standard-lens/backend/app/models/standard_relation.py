import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StandardRelationType(str, enum.Enum):
    REPLACES = "REPLACES"
    REPLACED_BY = "REPLACED_BY"
    AMENDS = "AMENDS"
    AMENDED_BY = "AMENDED_BY"
    RELATED = "RELATED"


class StandardRelation(Base):
    """Directed edge between two standards.

    Direction follows the field names: ``source REPLACES target`` means the
    source is the newer standard, while ``source REPLACED_BY target`` means the
    source is the older one. The version-chain endpoint traverses both
    directions, so either storage convention works. ``RELATED`` is a "see also"
    link and is intentionally not traversed by the version chain.
    """

    __tablename__ = "standard_relation"
    __table_args__ = (
        UniqueConstraint(
            "source_standard_id",
            "target_standard_id",
            "relation_type",
            name="uq_standard_relation_source_target_type",
        ),
        CheckConstraint(
            "source_standard_id <> target_standard_id",
            name="no_self",
        ),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_standard_id: Mapped[int] = mapped_column(
        ForeignKey("standard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_standard_id: Mapped[int] = mapped_column(
        ForeignKey("standard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[StandardRelationType] = mapped_column(
        Enum(
            StandardRelationType,
            name="standard_relation_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<StandardRelation id={self.id} "
            f"{self.source_standard_id}->{self.target_standard_id} "
            f"{self.relation_type!r}>"
        )
