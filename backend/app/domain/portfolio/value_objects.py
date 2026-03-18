"""Portfolio domain value objects."""

from __future__ import annotations

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


class PortfolioSnapshot(BaseModel):
    """Aggregated portfolio valuation at a point in time."""

    model_config = ConfigDict(frozen=True)

    holdings: list[HoldingValuation]
    total_market_value: Money
    total_cost_basis: Money
    total_pnl: Money
    total_pnl_pct: float
