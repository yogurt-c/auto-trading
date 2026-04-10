"""Initial schema — KIS broker integration

Revision ID: 001
Revises:
Create Date: 2026-04-10
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String, nullable=False, unique=True),
        sa.Column("shares", sa.Float, nullable=False),
        sa.Column("avg_price", sa.Float, nullable=False),
        sa.Column("market", sa.String, nullable=False, server_default="US"),
        sa.Column("currency", sa.String, nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("ticker", sa.String, nullable=True),
        sa.Column("strategy_type", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("ai_rationale", sa.Text, nullable=True),
        sa.Column("market", sa.String, nullable=False, server_default="US"),
        sa.Column("currency", sa.String, nullable=False, server_default="USD"),
        sa.Column("entry_price_drop_pct", sa.Float, nullable=True),
        sa.Column("entry_rsi_below", sa.Float, nullable=True),
        sa.Column("take_profit_pct", sa.Float, nullable=True),
        sa.Column("stop_loss_pct", sa.Float, nullable=True),
        sa.Column("sell_ratio", sa.Float, nullable=True),
        sa.Column("dca_amount", sa.Float, nullable=True),
        sa.Column("dca_frequency_days", sa.Integer, nullable=True),
        sa.Column("max_position", sa.Float, nullable=True),
        sa.Column("status", sa.String, server_default="active"),
        sa.Column("last_checked_at", sa.DateTime, nullable=True),
        sa.Column("last_triggered_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("shares", sa.Float, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("total", sa.Float, nullable=False),
        sa.Column("strategy_id", sa.Integer, sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("executed_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "trade_logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("strategy_id", sa.Integer, sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column("side", sa.String, nullable=False),
        sa.Column("qty", sa.Float, nullable=False),
        sa.Column("order_type", sa.String, nullable=False),
        sa.Column("limit_price", sa.Float, nullable=True),
        sa.Column("filled_price", sa.Float, nullable=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("broker_order_id", sa.String, nullable=True),
        sa.Column("market", sa.String, nullable=False, server_default="US"),
        sa.Column("currency", sa.String, nullable=False, server_default="USD"),
        sa.Column("ai_reasoning", sa.Text, nullable=True),
        sa.Column("avg_cost_snapshot", sa.Float, nullable=True),
        sa.Column("executed_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_trade_logs_broker_order_id "
        "ON trade_logs (broker_order_id) WHERE broker_order_id IS NOT NULL"
    )

    op.create_table(
        "realized_trades",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "trade_log_id",
            sa.Integer,
            sa.ForeignKey("trade_logs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column("qty", sa.Float, nullable=False),
        sa.Column("sell_price", sa.Float, nullable=False),
        sa.Column("avg_cost", sa.Float, nullable=False),
        sa.Column("realized_pnl", sa.Float, nullable=False),
        sa.Column("realized_pnl_pct", sa.Float, nullable=False),
        sa.Column("currency", sa.String, nullable=False, server_default="USD"),
        sa.Column(
            "strategy_id",
            sa.Integer,
            sa.ForeignKey("strategies.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("executed_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value", sa.String, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "scheduler_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("strategies_checked", sa.Integer, server_default="0"),
        sa.Column("orders_placed", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
    )
    op.create_index("ix_scheduler_runs_started_at", "scheduler_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scheduler_runs_started_at", table_name="scheduler_runs")
    op.drop_table("scheduler_runs")
    op.drop_table("settings")
    op.drop_table("realized_trades")
    op.execute("DROP INDEX IF EXISTS ix_trade_logs_broker_order_id")
    op.drop_table("trade_logs")
    op.drop_table("transactions")
    op.drop_table("strategies")
    op.drop_table("holdings")
