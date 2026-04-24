"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .timezone import now_kst


class Base(DeclarativeBase):
    pass


class DictMixin:
    __table__: Any  # SQLAlchemy 메타클래스가 주입하는 속성

    def to_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Holding(DictMixin, Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    shares: Mapped[float] = mapped_column(Float, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    market: Mapped[str] = mapped_column(String, nullable=False, default="US")  # 'KR' | 'US'
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")  # 'KRW' | 'USD'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst, onupdate=now_kst)



class Strategy(DictMixin, Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    strategy_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    ai_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    market: Mapped[str] = mapped_column(String, nullable=False, default="US")  # 'KR' | 'US'
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")  # 'KRW' | 'USD'
    entry_price_drop_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_rsi_below: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    dca_amount: Mapped[float | None] = mapped_column(Float, nullable=True)  # currency 단위
    dca_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_position: Mapped[float | None] = mapped_column(Float, nullable=True)  # currency 단위
    entry_bb_lower_touch: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    entry_macd_hist_positive: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    entry_disparity_below: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_volume_surge: Mapped[float | None] = mapped_column(Float, nullable=True)
    entry_sma_cross: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst, onupdate=now_kst)

    trade_logs: Mapped[list[TradeLog]] = relationship("TradeLog", back_populates="strategy")


class TradeLog(DictMixin, Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("strategies.id"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)  # 'buy' | 'sell'
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    order_type: Mapped[str] = mapped_column(String, nullable=False)  # 'market' | 'limit'
    limit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    filled_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    broker_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    market: Mapped[str] = mapped_column(String, nullable=False, default="US")  # 'KR' | 'US'
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")  # 'KRW' | 'USD'
    ai_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    avg_cost_snapshot: Mapped[float | None] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)

    strategy: Mapped[Strategy | None] = relationship("Strategy", back_populates="trade_logs")


class RealizedTrade(DictMixin, Base):
    __tablename__ = "realized_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_log_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trade_logs.id", ondelete="CASCADE"), nullable=False
    )
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    qty: Mapped[float] = mapped_column(Float, nullable=False)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False)
    avg_cost: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    realized_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")  # 'KRW' | 'USD'
    strategy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)


class Setting(DictMixin, Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst, onupdate=now_kst)


class SchedulerRun(DictMixin, Base):
    __tablename__ = "scheduler_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=now_kst)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)  # 'running' | 'success' | 'failed'
    strategies_checked: Mapped[int] = mapped_column(Integer, default=0)
    orders_placed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
