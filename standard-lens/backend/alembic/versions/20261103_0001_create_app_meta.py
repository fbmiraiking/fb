"""create app_meta table

Revision ID: 20261103_0001
Revises:
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_meta",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("meta_key", sa.String(length=64), nullable=False),
        sa.Column("meta_value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_meta")),
    )
    op.create_index(
        op.f("ix_app_meta_meta_key"),
        "app_meta",
        ["meta_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_app_meta_meta_key"), table_name="app_meta")
    op.drop_table("app_meta")
