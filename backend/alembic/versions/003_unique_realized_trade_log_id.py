"""Add unique constraint on realized_trades.trade_log_id.

Revision ID: 003
Revises: 002
Create Date: 2026-04-23
"""

from __future__ import annotations

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("realized_trades") as batch_op:
        batch_op.create_unique_constraint("uq_realized_trades_trade_log_id", ["trade_log_id"])


def downgrade() -> None:
    with op.batch_alter_table("realized_trades") as batch_op:
        batch_op.drop_constraint("uq_realized_trades_trade_log_id", type_="unique")
