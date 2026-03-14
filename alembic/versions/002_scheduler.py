"""Add scheduler support: Strategy timestamps + SchedulerRun table

Revision ID: 002
Revises: 001
Create Date: 2026-03-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add last_checked_at and last_triggered_at to strategies (SQLite batch mode)
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.add_column(sa.Column("last_checked_at", sa.DateTime, nullable=True))
        batch_op.add_column(sa.Column("last_triggered_at", sa.DateTime, nullable=True))

    # Create scheduler_runs table
    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("strategies_checked", sa.Integer, default=0),
        sa.Column("orders_placed", sa.Integer, default=0),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scheduler_runs")

    with op.batch_alter_table("strategies") as batch_op:
        batch_op.drop_column("last_triggered_at")
        batch_op.drop_column("last_checked_at")
