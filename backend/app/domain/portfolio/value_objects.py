"""Portfolio domain value objects."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class Money(BaseModel):
    """Represents a monetary amount (may be negative for P&L)."""

    model_config = ConfigDict(frozen=True)

    amount: float
    currency: str = "USD"

    @field_validator("amount")
    @classmethod
    def round_amount(cls, v: float) -> float:
        return round(v, 6)


class HoldingValuation(BaseModel):
    """Valuation snapshot for a single holding."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    shares: float
    avg_price: Money
    current_price: Money
    market_value: Money
    cost_basis: Money
    pnl: Money
    pnl_pct: float
    market: str = "US"  # "KR" | "US"
    currency: str = "USD"  # "KRW" | "USD"


class MarketSummary(BaseModel):
    """Aggregated valuation for a single market (KR or US)."""

    model_config = ConfigDict(frozen=True)

    market: str  # "KR" | "US"
    currency: str  # "KRW" | "USD"
    total_market_value: Money
    total_cost_basis: Money
    total_pnl: Money
    total_pnl_pct: float
    holding_count: int


class PortfolioSnapshot(BaseModel):
    """Aggregated portfolio valuation at a point in time, split by market."""

    model_config = ConfigDict(frozen=True)

    holdings: list[HoldingValuation]
    kr: MarketSummary | None = None  # None when no KR holdings
    us: MarketSummary | None = None  # None when no US holdings


class RealizedTradeVO(BaseModel):
    """Value object for a single realized trade row."""

    model_config = ConfigDict(frozen=True)

    id: int
    trade_log_id: int
    ticker: str
    qty: float
    sell_price: float
    avg_cost: float
    realized_pnl: float
    realized_pnl_pct: float
    currency: str = "USD"  # "KRW" | "USD"
    strategy_id: int | None
    strategy_name: str | None
    executed_at: datetime


class PeriodPnl(BaseModel):
    """Aggregated P&L for a single period bucket."""

    model_config = ConfigDict(frozen=True)

    period: str  # 'YYYY-MM-DD' (day) or 'YYYY-MM' (month)
    realized_pnl: float
    trade_count: int


class StrategyPnl(BaseModel):
    """Aggregated P&L per strategy."""

    model_config = ConfigDict(frozen=True)

    strategy_id: int | None
    strategy_name: str
    realized_pnl: float
    trade_count: int
    win_count: int
    win_rate: float


class PerformanceSummary(BaseModel):
    """Full performance report for a date range."""

    model_config = ConfigDict(frozen=True)

    period_start: str
    period_end: str
    total_realized_pnl: float
    total_trade_count: int
    win_count: int
    win_rate: float
    trades: list[RealizedTradeVO]
    by_period: list[PeriodPnl]
    by_strategy: list[StrategyPnl]
