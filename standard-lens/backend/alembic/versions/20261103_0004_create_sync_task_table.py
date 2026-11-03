"""create sync_task table

Revision ID: 20261103_0004
Revises: 20261103_0003
Create Date: 2026-11-03

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261103_0004"
down_revision: str | None = "20261103_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

sync_task_status = sa.Enum(
    "RUNNING",
    "SUCCESS",
    "PARTIAL",
    "FAILED",
    name="sync_task_status",
)


def upgrade() -> None:
    op.create_table(
        "sync_task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("total_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "status",
            sync_task_status,
            server_default="RUNNING",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_task")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        op.f("ix_sync_task_source"),
        "sync_task",
        ["source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sync_task_status"),
        "sync_task",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_task_status"), table_name="sync_task")
    op.drop_index(op.f("ix_sync_task_source"), table_name="sync_task")
    op.drop_table("sync_task")
