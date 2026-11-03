"""create product category and standard associations

Revision ID: 20261103_0005
Revises: 20261103_0004
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0005"
down_revision: str | None = "20261103_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

standard_product_relation_type = sa.Enum(
    "DIRECT_APPLICABLE",
    "MATERIAL",
    "SAFETY",
    "LABELING",
    "TEST_METHOD",
    "PACKAGING",
    "GENERAL",
    "POSSIBLE",
    name="standard_product_relation_type",
)
review_status = sa.Enum(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="review_status",
)


def upgrade() -> None:
    op.create_table(
        "product_category",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_category")),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["product_category.id"],
            name=op.f("fk_product_category_parent_id_product_category"),
            ondelete="SET NULL",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_product_category_parent_id"),
        "product_category",
        ["parent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_category_name"),
        "product_category",
        ["name"],
        unique=False,
    )

    op.create_table(
        "product_alias",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_alias")),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["product_category.id"],
            name=op.f("fk_product_alias_category_id_product_category"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "category_id",
            "alias",
            name="uq_product_alias_category_alias",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_product_alias_alias"),
        "product_alias",
        ["alias"],
        unique=False,
    )

    op.create_table(
        "standard_product_relation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=False),
        sa.Column("product_category_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", standard_product_relation_type, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "source_type",
            sa.String(length=32),
            server_default="MANUAL",
            nullable=False,
        ),
        sa.Column("source_reference", sa.String(length=512), nullable=True),
        sa.Column(
            "review_status",
            review_status,
            server_default="PENDING",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_standard_product_relation")),
        sa.ForeignKeyConstraint(
            ["product_category_id"],
            ["product_category.id"],
            name=op.f(
                "fk_standard_product_relation_product_category_id_product_category"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["standard.id"],
            name=op.f("fk_standard_product_relation_standard_id_standard"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "standard_id",
            "product_category_id",
            "relation_type",
            name="uq_standard_product_relation_std_category_type",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="confidence_range",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_standard_product_relation_product_category_id"),
        "standard_product_relation",
        ["product_category_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_standard_product_relation_review_status"),
        "standard_product_relation",
        ["review_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_standard_product_relation_review_status"),
        table_name="standard_product_relation",
    )
    op.drop_index(
        op.f("ix_standard_product_relation_product_category_id"),
        table_name="standard_product_relation",
    )
    op.drop_table("standard_product_relation")

    op.drop_index(op.f("ix_product_alias_alias"), table_name="product_alias")
    op.drop_table("product_alias")

    op.drop_index(op.f("ix_product_category_name"), table_name="product_category")
    op.drop_index(op.f("ix_product_category_parent_id"), table_name="product_category")
    op.drop_table("product_category")
