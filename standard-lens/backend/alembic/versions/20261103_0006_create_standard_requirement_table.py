"""create standard requirement table

Revision ID: 20261103_0006
Revises: 20261103_0005
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0006"
down_revision: str | None = "20261103_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

requirement_type = sa.Enum(
    "VISUAL",
    "LABEL",
    "DOCUMENT",
    "LAB_TEST",
    "MEASUREMENT",
    name="requirement_type",
)


def upgrade() -> None:
    op.create_table(
        "standard_requirement",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("standard_id", sa.Integer(), nullable=False),
        sa.Column("chapter", sa.String(length=64), nullable=False),
        sa.Column("requirement_type", requirement_type, nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("verification_method", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_standard_requirement")),
        sa.ForeignKeyConstraint(
            ["standard_id"],
            ["standard.id"],
            name=op.f("fk_standard_requirement_standard_id_standard"),
            ondelete="CASCADE",
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_standard_requirement_standard_id"),
        "standard_requirement",
        ["standard_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_standard_requirement_requirement_type"),
        "standard_requirement",
        ["requirement_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_standard_requirement_requirement_type"),
        table_name="standard_requirement",
    )
    op.drop_index(
        op.f("ix_standard_requirement_standard_id"),
        table_name="standard_requirement",
    )
    op.drop_table("standard_requirement")
