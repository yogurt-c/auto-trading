"""ETF 비중 교체(rotation) 백테스트 — R2 후보 A·B, 기준 B4, 변동성 돌파 D.

체결 규칙은 engine.py와 같다: t일 종가로 목표 비중을 정하고 t+1일 시가에 체결, 매도 먼저.
해외지수·채권 ETF는 매도 시 이익 난 건마다 매매차익 과세 (손익통산 없음).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import pandas as pd


@dataclass(frozen=True)
class AssetCosts:
    commission_rate: float
    slippage_rate: float
    gain_tax_rate: float = 0.0  # 0 = 국내 주식형 ETF (비과세)

    def with_slippage(self, slippage_rate: float) -> AssetCosts:
        return replace(self, slippage_rate=slippage_rate)


@dataclass
class _Holding:
    shares: int
    cost_per_share: float  # 수수료 포함 평균 취득가


@dataclass
class RotationResult:
    name: str
    equity: pd.Series
    trades: int
    taxes: float
    trade_log: list[tuple[pd.Timestamp, str, str, int, float]] = field(default_factory=list)


@dataclass
class _Book:
    cash: float
    costs: dict[str, AssetCosts]
    holdings: dict[str, _Holding] = field(default_factory=dict)
    taxes: float = 0.0
    log: list[tuple[pd.Timestamp, str, str, int, float]] = field(default_factory=list)

    def sell(self, day: pd.Timestamp, asset: str, qty: int, quote: float) -> None:
        held = self.holdings[asset]
        c = self.costs[asset]
        price = quote * (1 - c.slippage_rate)
        proceeds = qty * price * (1 - c.commission_rate)
        gain = proceeds - qty * held.cost_per_share
        tax = c.gain_tax_rate * gain if gain > 0 else 0.0
        self.cash += proceeds - tax
        self.taxes += tax
        held.shares -= qty
        if held.shares == 0:
            del self.holdings[asset]
        self.log.append((day, asset, "sell", qty, price))

    def buy(self, day: pd.Timestamp, asset: str, qty: int, quote: float) -> None:
        c = self.costs[asset]
        price = quote * (1 + c.slippage_rate)
        unit = price * (1 + c.commission_rate)
        qty = min(qty, int(self.cash // unit))
        if qty <= 0:
            return
        self.cash -= qty * unit
        held = self.holdings.get(asset)
        if held is None:
            self.holdings[asset] = _Holding(qty, unit)
        else:
            total = held.shares + qty
            held.cost_per_share = (held.cost_per_share * held.shares + unit * qty) / total
            held.shares = total
        self.log.append((day, asset, "buy", qty, price))

    def equity(self, prices: dict[str, pd.DataFrame], day: pd.Timestamp) -> float:
        return self.cash + sum(
            h.shares * float(prices[a].at[day, "close"]) for a, h in self.holdings.items()
        )


def run_rotation(
    name: str,
    prices: dict[str, pd.DataFrame],
    targets: dict[pd.Timestamp, dict[str, float]],
    days: pd.DatetimeIndex,
    capital: float,
    costs: dict[str, AssetCosts],
    cash_buffer: float = 0.005,
) -> RotationResult:
    """targets: 판단일 → {자산: 비중}. 판단일 종가 기준 수량을 다음 날 시가에 맞춘다."""
    book = _Book(cash=capital, costs=costs)
    pending: dict[str, int] | None = None
    equity: dict[pd.Timestamp, float] = {}
    for i, day in enumerate(days):
        if pending is not None:
            _execute(book, day, pending, prices)
            pending = None
        equity[day] = book.equity(prices, day)
        if day in targets and i < len(days) - 1:
            pending = _target_shares(targets[day], equity[day] * (1 - cash_buffer), prices, day)
    trades = len(book.log)
    return RotationResult(name, pd.Series(equity, name=name), trades, book.taxes, book.log)


def _target_shares(
    weights: dict[str, float], budget: float, prices: dict[str, pd.DataFrame], day: pd.Timestamp
) -> dict[str, int]:
    return {
        asset: int(budget * w // float(prices[asset].at[day, "close"]))
        for asset, w in weights.items()
        if w > 0
    }


def _execute(
    book: _Book, day: pd.Timestamp, target: dict[str, int], prices: dict[str, pd.DataFrame]
) -> None:
    for asset in list(book.holdings):
        diff = target.get(asset, 0) - book.holdings[asset].shares
        if diff < 0:
            book.sell(day, asset, -diff, float(prices[asset].at[day, "open"]))
    for asset, qty in target.items():
        held = book.holdings.get(asset)
        diff = qty - (held.shares if held else 0)
        if diff > 0:
            book.buy(day, asset, diff, float(prices[asset].at[day, "open"]))


def run_breakout(
    name: str,
    ohlc: pd.DataFrame,
    days: pd.DatetimeIndex,
    capital: float,
    costs: AssetCosts,
    k: float,
) -> RotationResult:
    """변동성 돌파: 목표가 = 시가 + k * (전일 고가 - 전일 저가).

    고가가 목표가에 닿으면 max(시가, 목표가)에 전액 매수, 다음 거래일 시가에 전량 매도.
    판단에 쓰는 전일 고저는 기간 시작 전 날짜도 쓴다 (워밍업).
    """
    book = _Book(cash=capital, costs={"x": costs})
    equity: dict[pd.Timestamp, float] = {}
    prev_range = (ohlc["high"] - ohlc["low"]).shift(1)
    frame = {"x": ohlc}
    for day in days:
        row = ohlc.loc[day]
        if "x" in book.holdings:
            book.sell(day, "x", book.holdings["x"].shares, float(row["open"]))
        target = float(row["open"]) + k * float(prev_range.at[day])
        if pd.notna(target) and float(row["high"]) >= target and day != days[-1]:
            fill_quote = max(float(row["open"]), target)
            unit = fill_quote * (1 + costs.slippage_rate) * (1 + costs.commission_rate)
            book.buy(day, "x", int(book.cash // unit), fill_quote)
        equity[day] = book.equity(frame, day)
    return RotationResult(name, pd.Series(equity, name=name), len(book.log), book.taxes, book.log)
