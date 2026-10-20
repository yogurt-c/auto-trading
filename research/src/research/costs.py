"""거래 비용 모델 — 수수료, 날짜별 증권거래세, 슬리피지."""

from __future__ import annotations

import bisect
from dataclasses import dataclass, replace
from datetime import date

import pandas as pd


@dataclass(frozen=True)
class CostModel:
    commission_rate: float
    slippage_rate: float
    tax_schedule: tuple[tuple[date, float], ...]  # (적용 시작일, 세율), 오름차순
    taxed: bool = True  # ETF 매도는 거래세 면제

    @classmethod
    def from_config(cls, cfg: dict, *, etf: bool = False) -> CostModel:
        schedule = tuple(
            sorted((date.fromisoformat(d), float(r)) for d, r in cfg["sell_tax_kospi"].items())
        )
        return cls(
            commission_rate=cfg["commission_rate"],
            slippage_rate=cfg["etf_slippage_rate"] if etf else cfg["slippage_rate"],
            tax_schedule=schedule,
            taxed=not etf,
        )

    def with_slippage(self, slippage_rate: float) -> CostModel:
        return replace(self, slippage_rate=slippage_rate)

    def sell_tax_rate(self, day: date | pd.Timestamp) -> float:
        if not self.taxed:
            return 0.0
        d = day.date() if isinstance(day, pd.Timestamp) else day
        starts = [s for s, _ in self.tax_schedule]
        idx = bisect.bisect_right(starts, d) - 1
        return self.tax_schedule[idx][1] if idx >= 0 else 0.0

    def buy_price(self, quote: float) -> float:
        return quote * (1 + self.slippage_rate)

    def sell_price(self, quote: float) -> float:
        return quote * (1 - self.slippage_rate)

    def buy_cash_out(self, qty: float, fill_price: float) -> float:
        """매수 시 빠져나가는 현금 (체결금액 + 수수료)."""
        return qty * fill_price * (1 + self.commission_rate)

    def sell_cash_in(self, qty: float, fill_price: float, day: date | pd.Timestamp) -> float:
        """매도 시 들어오는 현금 (체결금액 - 수수료 - 거래세)."""
        return qty * fill_price * (1 - self.commission_rate - self.sell_tax_rate(day))
