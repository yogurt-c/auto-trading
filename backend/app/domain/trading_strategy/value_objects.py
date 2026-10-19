"""TradingStrategy domain value objects."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ValidationSeverity(StrEnum):
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
    currency: str = "USD"  # 'KRW' | 'USD'
    market: Literal["KR", "US"] = "US"
    high_30d: float | None = None
    rsi_14: float | None = None
    # 이동평균
    sma_20: float | None = None
    sma_60: float | None = None
    ema_12: float | None = None
    ema_26: float | None = None
    # MACD
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    # 볼린저 밴드
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    # 보조 지표
    disparity_20: float | None = None
    atr_14: float | None = None
    volume_ratio_20: float | None = None


class EvaluationResult(BaseModel):
    """Result of evaluating a strategy's entry/exit conditions."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    current_price: float
    entry_triggered: bool
    exit_triggered: bool
    conditions: dict[str, Any]
    signal_score: float | None = None  # 0.0 ~ 1.0: 발동된 진입 조건 비율
    holding_avg_price: float | None = None
    current_pnl_pct: float | None = None
    note: str | None = None


class GateDecision(BaseModel):
    """EntryGate 결과 — 진입 신호를 실제 매수로 이어갈지 여부."""

    model_config = ConfigDict(frozen=True)

    entry_allowed: bool
    blocked_reason: str | None = None
