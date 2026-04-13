"""Add indicator-based entry condition columns to strategies table.

Revision ID: 002
Revises: 001
Create Date: 2026-04-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.add_column(sa.Column("entry_bb_lower_touch", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("entry_macd_hist_positive", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("entry_disparity_below", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("entry_volume_surge", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("entry_sma_cross", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.drop_column("entry_sma_cross")
        batch_op.drop_column("entry_volume_surge")
        batch_op.drop_column("entry_disparity_below")
        batch_op.drop_column("entry_macd_hist_positive")
        batch_op.drop_column("entry_bb_lower_touch")
