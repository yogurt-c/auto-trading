"""Bug fixes: avg_cost_snapshot, scheduler index, alpaca_id unique constraint

Revision ID: 005
Revises: 004
Create Date: 2026-03-30
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Issue 6+7: trade_logs에 avg_cost_snapshot 컬럼 추가
    with op.batch_alter_table("trade_logs") as batch_op:
        batch_op.add_column(sa.Column("avg_cost_snapshot", sa.Float, nullable=True))

    # Issue 12: scheduler_runs.started_at 인덱스
    op.create_index("ix_scheduler_runs_started_at", "scheduler_runs", ["started_at"])

    # Issue 13: trade_logs.alpaca_id 유니크 인덱스 (NULL 제외)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_trade_logs_alpaca_id "
        "ON trade_logs (alpaca_id) WHERE alpaca_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_trade_logs_alpaca_id")
    op.drop_index("ix_scheduler_runs_started_at", table_name="scheduler_runs")
    with op.batch_alter_table("trade_logs") as batch_op:
        batch_op.drop_column("avg_cost_snapshot")
