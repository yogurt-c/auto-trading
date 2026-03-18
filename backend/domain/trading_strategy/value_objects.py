"""TradingStrategy domain value objects."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ValidationSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class ValidationWarning(BaseModel):
    """A single strategy parameter validation warning."""

    model_config = ConfigDict(frozen=True)

    message: str
    severity: ValidationSeverity = ValidationSeverity.WARNING


class MarketData(BaseModel):
    """Market data snapshot injected into StrategyEvaluator (no I/O)."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    current_price: float
    high_30d: float | None = None
    rsi_14: float | None = None


class EvaluationResult(BaseModel):
    """Result of evaluating a strategy's entry/exit conditions."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    current_price: float
    entry_triggered: bool
    exit_triggered: bool
    conditions: dict[str, Any]
    holding_avg_price: float | None = None
    current_pnl_pct: float | None = None
    note: str | None = None
