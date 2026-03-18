"""Convert UTC datetimes to KST (+9h)

Revision ID: 003
Revises: 002
Create Date: 2026-03-18
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# func.now() (server_default) 로 저장된 컬럼들만 +9시간 변환
# last_checked_at, last_triggered_at, finished_at 은 datetime.now() (KST naive) 저장이므로 제외
UTC_COLUMNS = [
    ("holdings",       ["created_at", "updated_at"]),
    ("transactions",   ["executed_at"]),
    ("strategies",     ["created_at", "updated_at"]),
    ("trade_logs",     ["executed_at"]),
    ("settings",       ["updated_at"]),
    ("scheduler_runs", ["started_at"]),
]


def upgrade() -> None:
    for table, cols in UTC_COLUMNS:
        for col in cols:
            op.execute(
                f"UPDATE {table} SET {col} = datetime({col}, '+9 hours') "
                f"WHERE {col} IS NOT NULL"
            )


def downgrade() -> None:
    for table, cols in UTC_COLUMNS:
        for col in cols:
            op.execute(
                f"UPDATE {table} SET {col} = datetime({col}, '-9 hours') "
                f"WHERE {col} IS NOT NULL"
            )
