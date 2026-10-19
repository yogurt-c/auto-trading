"""시뮬레이션용 계좌 상태 — 현금, 보유 종목, 체결 기록."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from research.costs import CostModel


@dataclass
class Position:
    shares: float  # 권리락 조정 후 소수 주가 생길 수 있음
    avg_price: float


@dataclass(frozen=True)
class Fill:
    date: pd.Timestamp
    code: str
    side: str  # "buy" | "sell"
    qty: float
    price: float
    reason: str


@dataclass
class Portfolio:
    cash: float
    costs: CostModel
    positions: dict[str, Position] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)
    dividends_received: float = 0.0

    def buy(self, day: pd.Timestamp, code: str, qty: float, quote: float, reason: str) -> float:
        """현금 한도 안에서 매수. 실제 체결 수량을 반환한다."""
        price = self.costs.buy_price(quote)
        affordable = int(self.cash // (price * (1 + self.costs.commission_rate)))
        qty = min(qty, affordable)
        if qty <= 0:
            return 0
        self.cash -= self.costs.buy_cash_out(qty, price)
        held = self.positions.get(code)
        if held is None:
            self.positions[code] = Position(shares=qty, avg_price=price)
        else:
            total = held.shares + qty
            held.avg_price = (held.avg_price * held.shares + price * qty) / total
            held.shares = total
        self.fills.append(Fill(day, code, "buy", qty, price, reason))
        return qty

    def sell(self, day: pd.Timestamp, code: str, qty: float, quote: float, reason: str) -> float:
        held = self.positions.get(code)
        if held is None or qty <= 0:
            return 0
        qty = min(qty, held.shares)
        price = self.costs.sell_price(quote)
        self.cash += self.costs.sell_cash_in(qty, price, day)
        held.shares -= qty
        if held.shares <= 1e-9:
            del self.positions[code]
        self.fills.append(Fill(day, code, "sell", qty, price, reason))
        return qty

    def apply_adjustment(self, code: str, factor: float) -> None:
        """분할·권리락: 가격이 factor배가 되면 주식 수는 1/factor배, 평단은 factor배."""
        held = self.positions.get(code)
        if held is None or factor == 1.0:
            return
        held.shares /= factor
        held.avg_price *= factor

    def credit_dividend(self, code: str, dps: float, tax_rate: float) -> None:
        held = self.positions.get(code)
        if held is None:
            return
        amount = held.shares * dps * (1 - tax_rate)
        self.cash += amount
        self.dividends_received += amount

    def equity(self, prices: dict[str, float]) -> float:
        return self.cash + sum(p.shares * prices[c] for c, p in self.positions.items())

    def position_value(self, code: str, price: float) -> float:
        held = self.positions.get(code)
        return held.shares * price if held else 0.0
