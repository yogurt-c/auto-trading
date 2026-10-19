"""일 단위 이벤트 루프 백테스트 엔진.

하루의 순서 (t일):
  1. 분할·권리락 반영 (보유 주식 수·평단 조정)
  2. 전날 결정한 주문을 t일 시가에 체결 — 매도 먼저, 매수 나중. 시가가 없으면(거래정지) 취소
  3. 상장폐지(데이터 종료) 종목은 마지막 종가로 강제 청산
  4. 연말 마지막 거래일에 보유 종목 현금배당(세후) 입금
  5. 종가로 평가
  6. t일 종가까지의 완결 일봉으로 다음 날 주문 결정 —
     StrategyEvaluator(조건) → EntryGate(한도·점수) → [국면·공시 필터] → OrderSizer(수량)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pandas as pd

from app.domain.trading_strategy.services import EntryGate, OrderSizer, StrategyEvaluator
from research.costs import CostModel
from research.market_data import to_market_data
from research.portfolio import Fill, Portfolio


@dataclass(frozen=True)
class MarketInputs:
    """엔진 입력 — 파라미터와 무관하게 한 번 만들어 재사용한다."""

    opens: pd.DataFrame  # date x code, 원주가
    closes: pd.DataFrame
    factors: pd.DataFrame  # 분할·권리락 계수 (이벤트 없으면 1.0)
    market_data: Mapping[tuple[str, pd.Timestamp], dict]  # dict 또는 MarketDataStore
    universe: pd.DataFrame  # rebalance_date, code, rank
    regime_ok: pd.Series  # date → 지수 > SMA200 (해당일 종가 기준)
    veto_until: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]]  # code → 진입 금지 구간
    dividends: dict[tuple[str, int], float]  # (code, 사업연도) → 주당 현금배당금
    last_trade_date: dict[str, pd.Timestamp]

    @property
    def trading_days(self) -> pd.DatetimeIndex:
        return self.closes.index


@dataclass(frozen=True)
class StrategySpec:
    name: str
    params: dict  # StrategyEvaluator strategy dict와 같은 키
    use_regime_filter: bool = False
    use_disclosure_veto: bool = False


@dataclass(frozen=True)
class EqualWeightSpec:
    """B3 기준 전략: 시점별 유니버스 동일비중, 유니버스가 바뀌는 날(분기) 리밸런싱."""

    name: str = "B3_equal_weight"
    cash_buffer: float = 0.005  # 비용 여유분


@dataclass(frozen=True)
class Order:
    code: str
    side: str
    qty: float
    reason: str


@dataclass
class BacktestResult:
    spec: StrategySpec | EqualWeightSpec
    equity: pd.Series
    fills: list[Fill]
    blocked_by_veto: list[tuple[pd.Timestamp, str]] = field(default_factory=list)
    dividends: float = 0.0

    @property
    def entries(self) -> int:
        return sum(1 for f in self.fills if f.side == "buy")


@dataclass(frozen=True)
class EngineConfig:
    capital: float
    max_position_pct: float
    dividend_tax_rate: float


class Engine:
    def __init__(self, inputs: MarketInputs, config: EngineConfig, costs: CostModel) -> None:
        self._in = inputs
        self._cfg = config
        self._costs = costs
        self._evaluator = StrategyEvaluator()
        self._gate = EntryGate()
        self._sizer = OrderSizer()
        days = pd.Series(inputs.trading_days, index=inputs.trading_days)
        self._year_end_days = set(days.groupby(days.index.year).max())
        universe = inputs.universe.sort_values(["rebalance_date", "rank"])
        self._rebalance_dates = pd.DatetimeIndex(sorted(universe["rebalance_date"].unique()))
        self._members_by_date = {
            d: list(zip(g["code"], g["rank"], strict=True))
            for d, g in universe.groupby("rebalance_date")
        }

    def run(
        self,
        spec: StrategySpec | EqualWeightSpec,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> BacktestResult:
        days = self._in.trading_days[
            (self._in.trading_days >= start) & (self._in.trading_days <= end)
        ]
        book = Portfolio(cash=self._cfg.capital, costs=self._costs)
        last_price: dict[str, float] = {}
        pending: list[Order] = []
        equity: dict[pd.Timestamp, float] = {}
        blocked: list[tuple[pd.Timestamp, str]] = []

        for i, day in enumerate(days):
            self._apply_adjustments(book, day)
            self._execute(book, day, pending)
            self._liquidate_delisted(book, day, last_price)
            self._credit_dividends(book, day)
            self._update_prices(book, day, last_price)
            equity[day] = book.equity(last_price)
            if i == len(days) - 1:
                pending = []
            elif isinstance(spec, EqualWeightSpec):
                pending = self._decide_equal_weight(spec, book, day, days[i + 1], equity[day])
            else:
                pending = self._decide(spec, book, day, equity[day], blocked)

        return BacktestResult(
            spec=spec,
            equity=pd.Series(equity, name=spec.name),
            fills=book.fills,
            blocked_by_veto=blocked,
            dividends=book.dividends_received,
        )

    # --- 하루 처리 단계 ---------------------------------------------------

    def _apply_adjustments(self, book: Portfolio, day: pd.Timestamp) -> None:
        for code in list(book.positions):
            factor = self._in.factors.at[day, code] if code in self._in.factors else 1.0
            if pd.notna(factor) and factor != 1.0:
                book.apply_adjustment(code, float(factor))

    def _execute(self, book: Portfolio, day: pd.Timestamp, orders: list[Order]) -> None:
        for order in sorted(orders, key=lambda o: o.side != "sell"):
            quote = self._in.opens.at[day, order.code]
            if pd.isna(quote):
                continue
            if order.side == "sell":
                book.sell(day, order.code, order.qty, float(quote), order.reason)
            else:
                book.buy(day, order.code, order.qty, float(quote), order.reason)

    def _liquidate_delisted(
        self, book: Portfolio, day: pd.Timestamp, last_price: dict[str, float]
    ) -> None:
        for code in list(book.positions):
            if self._in.last_trade_date[code] < day:
                shares = book.positions[code].shares
                book.sell(day, code, shares, last_price[code], "delisted")

    def _credit_dividends(self, book: Portfolio, day: pd.Timestamp) -> None:
        """사업연도 배당을 그해 마지막 거래일 보유분에 입금 (기준일 = 연말 근사)."""
        if day not in self._year_end_days:
            return
        for code in list(book.positions):
            dps = self._in.dividends.get((code, day.year))
            if dps:
                book.credit_dividend(code, dps, self._cfg.dividend_tax_rate)

    def _update_prices(
        self, book: Portfolio, day: pd.Timestamp, last_price: dict[str, float]
    ) -> None:
        row = self._in.closes.loc[day]
        for code in book.positions:
            close = row.get(code)
            if pd.notna(close):
                last_price[code] = float(close)

    # --- 주문 결정 --------------------------------------------------------

    def _decide(
        self,
        spec: StrategySpec,
        book: Portfolio,
        day: pd.Timestamp,
        equity: float,
        blocked: list[tuple[pd.Timestamp, str]],
    ) -> list[Order]:
        orders: list[Order] = []
        selling: set[str] = set()
        projected_cash = book.cash

        for code, held in book.positions.items():
            md_row = self._in.market_data.get((code, day))
            if md_row is None:
                continue
            holding = {"avg_price": held.avg_price, "shares": held.shares}
            result = self._evaluator.evaluate(spec.params, to_market_data(md_row), holding)
            if result.exit_triggered:
                qty = self._sell_qty(held.shares, spec.params.get("sell_ratio"))
                orders.append(Order(code, "sell", qty, _reason(result.conditions, "exit")))
                selling.add(code)
                projected_cash += self._costs.sell_cash_in(qty, md_row["current_price"], day)

        if spec.use_regime_filter and not bool(self._in.regime_ok.get(day, False)):
            return orders

        max_position = self._cfg.max_position_pct * equity
        params = {**spec.params, "max_position": max_position}
        candidates = []
        for code, rank in self._members(day):
            md_row = self._in.market_data.get((code, day))
            if code in selling or md_row is None:
                continue
            result = self._evaluator.evaluate(params, to_market_data(md_row), None)
            price = md_row["current_price"]
            position_value = book.position_value(code, price)
            if not self._gate.apply(params, result, position_value).entry_allowed:
                continue
            if spec.use_disclosure_veto and self._is_vetoed(code, day):
                blocked.append((day, code))
                continue
            candidates.append((-(result.signal_score or 0.0), rank, code, price, position_value))

        for _, _, code, price, position_value in sorted(candidates):
            qty = self._sizer.buy_qty(max_position, position_value, price, projected_cash)
            if qty > 0:
                orders.append(Order(code, "buy", qty, "entry"))
                projected_cash -= self._costs.buy_cash_out(qty, self._costs.buy_price(price))
        return orders

    def _decide_equal_weight(
        self,
        spec: EqualWeightSpec,
        book: Portfolio,
        day: pd.Timestamp,
        next_day: pd.Timestamp,
        equity: float,
    ) -> list[Order]:
        members = {code for code, _ in self._members(next_day)}
        is_first_day = not book.positions and not book.fills
        if not members or (
            members == {code for code, _ in self._members(day)} and not is_first_day
        ):
            return []
        closes = self._in.closes.loc[day]
        target = equity * (1 - spec.cash_buffer) / len(members)
        orders = [
            Order(code, "sell", held.shares, "rebalance_out")
            for code, held in book.positions.items()
            if code not in members
        ]
        for code in sorted(members):
            price = closes.get(code)
            if pd.isna(price):
                continue
            diff = target - book.position_value(code, float(price))
            qty = int(abs(diff) // float(price))
            if qty > 0:
                orders.append(Order(code, "buy" if diff > 0 else "sell", qty, "rebalance"))
        return orders

    def _members(self, day: pd.Timestamp) -> list[tuple[str, int]]:
        """day보다 이전의 가장 최근 리밸런싱 (code, rank) — universe.members_on과 같은 규칙."""
        i = self._rebalance_dates.searchsorted(day, side="left") - 1
        return self._members_by_date[self._rebalance_dates[i]] if i >= 0 else []

    def _sell_qty(self, shares: float, sell_ratio: float | None) -> float:
        whole = int(shares)
        qty = self._sizer.sell_qty(whole, sell_ratio)
        return shares if qty >= whole else qty  # 전량 매도면 권리락 소수 주까지 청산

    def _is_vetoed(self, code: str, day: pd.Timestamp) -> bool:
        return any(lo <= day <= hi for lo, hi in self._in.veto_until.get(code, ()))


def _reason(conditions: dict, kind: str) -> str:
    keys = ("take_profit", "stop_loss") if kind == "exit" else ()
    hit = [k for k in keys if conditions.get(k, {}).get("triggered")]
    return ",".join(hit) or kind
