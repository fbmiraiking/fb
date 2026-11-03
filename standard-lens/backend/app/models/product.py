from __future__ import annotations

import enum
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProductCategory(Base):
    """A product category, optionally nested under a parent category."""

    __tablename__ = "product_category"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_category.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    aliases: Mapped[list["ProductAlias"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<ProductCategory id={self.id} name={self.name!r}>"


class ProductAlias(Base):
    """Alternative search name for a product category."""

    __tablename__ = "product_alias"
    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "alias",
            name="uq_product_alias_category_alias",
        ),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("product_category.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    category: Mapped[ProductCategory] = relationship(back_populates="aliases")

    def __repr__(self) -> str:
        return f"<ProductAlias id={self.id} alias={self.alias!r}>"


class StandardProductRelationType(str, enum.Enum):
    DIRECT_APPLICABLE = "DIRECT_APPLICABLE"
    MATERIAL = "MATERIAL"
    SAFETY = "SAFETY"
    LABELING = "LABELING"
    TEST_METHOD = "TEST_METHOD"
    PACKAGING = "PACKAGING"
    GENERAL = "GENERAL"
    POSSIBLE = "POSSIBLE"


class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class StandardProductRelation(Base):
    """Association between a standard and a product category.

    A standard can have several relation types for the same category, but the
    public product endpoint returns one item per standard, choosing the most
    relevant relation type.
    """

    __tablename__ = "standard_product_relation"
    __table_args__ = (
        UniqueConstraint(
            "standard_id",
            "product_category_id",
            "relation_type",
            name="uq_standard_product_relation_std_category_type",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_0900_ai_ci"},
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        ForeignKey("standard.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_category_id: Mapped[int] = mapped_column(
        ForeignKey("product_category.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[StandardProductRelationType] = mapped_column(
        Enum(
            StandardProductRelationType,
            name="standard_product_relation_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )
    confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="MANUAL",
        server_default="MANUAL",
    )
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(
            ReviewStatus,
            name="review_status",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<StandardProductRelation id={self.id} "
            f"standard={self.standard_id} category={self.product_category_id} "
            f"type={self.relation_type!r}>"
        )
