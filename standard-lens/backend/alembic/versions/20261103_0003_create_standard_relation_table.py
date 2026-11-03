"""create standard_relation table

Revision ID: 20261103_0003
Revises: 20261103_0002
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0003"
down_revision: str | None = "20261103_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

standard_relation_type = sa.Enum(
    "REPLACES",
    "REPLACED_BY",
    "AMENDS",
    "AMENDED_BY",
    "RELATED",
    name="standard_relation_type",
)


def upgrade() -> None:
    op.create_table(
        "standard_relation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_standard_id", sa.Integer(), nullable=False),
        sa.Column("target_standard_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", standard_relation_type, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_standard_relation")),
        sa.ForeignKeyConstraint(
            ["source_standard_id"],
            ["standard.id"],
            name=op.f("fk_standard_relation_source_standard_id_standard"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_standard_id"],
            ["standard.id"],
            name=op.f("fk_standard_relation_target_standard_id_standard"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "source_standard_id",
            "target_standard_id",
            "relation_type",
            name="uq_standard_relation_source_target_type",
        ),
        sa.CheckConstraint(
            "source_standard_id <> target_standard_id",
            name="no_self",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_standard_relation_source_standard_id"),
        "standard_relation",
        ["source_standard_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_standard_relation_target_standard_id"),
        "standard_relation",
        ["target_standard_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_standard_relation_target_standard_id"),
        table_name="standard_relation",
    )
    op.drop_index(
        op.f("ix_standard_relation_source_standard_id"),
        table_name="standard_relation",
    )
    op.drop_table("standard_relation")
