"""Add realized_trades table and trade_logs.filled_price

Revision ID: 004
Revises: 003
Create Date: 2026-03-27
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. trade_logs에 체결가 컬럼 추가 (기존 레코드는 NULL)
    op.add_column("trade_logs", sa.Column("filled_price", sa.Float, nullable=True))

    # 2. realized_trades 테이블 신규 생성
    op.create_table(
        "realized_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "trade_log_id",
            sa.Integer,
            sa.ForeignKey("trade_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("qty", sa.Float, nullable=False),
        sa.Column("sell_price", sa.Float, nullable=False),
        sa.Column("avg_cost", sa.Float, nullable=False),
        sa.Column("realized_pnl", sa.Float, nullable=False),
        sa.Column("realized_pnl_pct", sa.Float, nullable=False),
        sa.Column(
            "strategy_id",
            sa.Integer,
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("executed_at", sa.DateTime, nullable=False),
    )

    # 3. 인덱스 생성
    op.create_index("idx_rt_executed_at", "realized_trades", ["executed_at"])
    op.create_index("idx_rt_strategy_id", "realized_trades", ["strategy_id"])
    op.create_index("idx_rt_ticker", "realized_trades", ["ticker"])


def downgrade() -> None:
    op.drop_index("idx_rt_ticker", table_name="realized_trades")
    op.drop_index("idx_rt_strategy_id", table_name="realized_trades")
    op.drop_index("idx_rt_executed_at", table_name="realized_trades")
    op.drop_table("realized_trades")
    op.drop_column("trade_logs", "filled_price")
