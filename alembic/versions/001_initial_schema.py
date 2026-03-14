"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-13
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
        sa.Column("entry_price_drop_pct", sa.Float, nullable=True),
        sa.Column("entry_rsi_below", sa.Float, nullable=True),
        sa.Column("take_profit_pct", sa.Float, nullable=True),
        sa.Column("stop_loss_pct", sa.Float, nullable=True),
        sa.Column("sell_ratio", sa.Float, nullable=True),
        sa.Column("dca_amount_usd", sa.Float, nullable=True),
        sa.Column("dca_frequency_days", sa.Integer, nullable=True),
        sa.Column("max_position_usd", sa.Float, nullable=True),
        sa.Column("status", sa.String, server_default="active"),
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
        sa.Column("status", sa.String, nullable=False),
        sa.Column("alpaca_id", sa.String, nullable=True),
        sa.Column("ai_reasoning", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String, primary_key=True),
        sa.Column("value", sa.String, nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("trade_logs")
    op.drop_table("transactions")
    op.drop_table("strategies")
    op.drop_table("holdings")
    op.drop_table("settings")
