"""create standard table

Revision ID: 20261103_0002
Revises: 20261103_0001
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0002"
down_revision: str | None = "20261103_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

standard_status = sa.Enum(
    "UPCOMING",
    "ACTIVE",
    "REPLACED",
    "ABOLISHED",
    "UNKNOWN",
    name="standard_status",
)


def upgrade() -> None:
    op.create_table(
        "standard",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_no", sa.String(length=128), nullable=False),
        sa.Column("normalized_no", sa.String(length=128), nullable=False),
        sa.Column("standard_name", sa.String(length=512), nullable=False),
        sa.Column("standard_type", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            standard_status,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("publish_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("standard_year", sa.Integer(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("source_url", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_standard")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_standard_standard_no"),
        "standard",
        ["standard_no"],
        unique=False,
    )
    op.create_index(
        op.f("ix_standard_normalized_no"),
        "standard",
        ["normalized_no"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_standard_normalized_no"), table_name="standard")
    op.drop_index(op.f("ix_standard_standard_no"), table_name="standard")
    op.drop_table("standard")
