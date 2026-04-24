"""Drop unused transactions table (replaced by trade_logs).

Revision ID: 004
Revises: 003
Create Date: 2026-04-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("transactions")


def downgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker", sa.String, nullable=False),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("shares", sa.Float, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("total", sa.Float, nullable=False),
        sa.Column("strategy_id", sa.Integer, sa.ForeignKey("strategies.id"), nullable=True),
        sa.Column("executed_at", sa.DateTime, server_default=sa.func.current_timestamp()),
    )
