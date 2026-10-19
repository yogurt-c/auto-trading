"""백테스트 엔진 테스트 — 합성 시세로 체결 시점·비용·분할·상장폐지·필터를 검증."""

from datetime import date

import numpy as np
import pandas as pd
import pytest

from research.baselines import buy_and_hold, monthly_dca
from research.costs import CostModel
from research.engine import (
    Engine,
    EngineConfig,
    EqualWeightSpec,
    MarketInputs,
    StrategySpec,
)
from research.portfolio import Portfolio

DAYS = pd.bdate_range("2020-01-01", periods=10)
NO_COSTS = CostModel(0.0, 0.0, ((date(1900, 1, 1), 0.0),))
CONFIG = EngineConfig(capital=1_000_000, max_position_pct=0.3, dividend_tax_rate=0.0)
RSI_ONLY = {"entry_rsi_below": 30.0, "take_profit_pct": 10.0, "stop_loss_pct": -50.0}


def _inputs(
    closes: dict[str, list[float]],
    rsi: dict[str, list[float]],
    *,
    opens: dict[str, list[float]] | None = None,
    factors: dict[str, list[float]] | None = None,
    days: pd.DatetimeIndex = DAYS,
    regime: list[bool] | None = None,
    veto: dict | None = None,
    dividends: dict | None = None,
) -> MarketInputs:
    close_df = pd.DataFrame(closes, index=days)
    open_df = pd.DataFrame(opens, index=days) if opens else close_df.copy()
    factor_df = (
        pd.DataFrame(factors, index=days)
        if factors
        else pd.DataFrame(1.0, index=days, columns=close_df.columns)
    )
    market_data = {}
    for code in closes:
        for day, c, r in zip(days, closes[code], rsi[code], strict=True):
            if not np.isnan(c):
                market_data[(code, day)] = {"ticker": code, "current_price": c, "rsi_14": r}
    universe = pd.DataFrame(
        {"rebalance_date": days[0] - pd.Timedelta(days=1), "code": list(closes), "rank": 1}
    )
    last_trade = {code: close_df[code].last_valid_index() for code in closes}
    return MarketInputs(
        opens=open_df,
        closes=close_df,
        factors=factor_df,
        market_data=market_data,
        universe=universe,
        regime_ok=pd.Series(regime if regime else [True] * len(days), index=days),
        veto_until=veto or {},
        dividends=dividends or {},
        last_trade_date=last_trade,
    )


def _run(inputs: MarketInputs, spec=None, costs=NO_COSTS, config=CONFIG):
    spec = spec or StrategySpec("t", RSI_ONLY)
    return Engine(inputs, config, costs).run(spec, inputs.trading_days[0], inputs.trading_days[-1])


class TestCostModel:
    def test_sell_tax_follows_schedule(self):
        cfg = {
            "commission_rate": 0.0,
            "slippage_rate": 0.0,
            "etf_slippage_rate": 0.0,
            "sell_tax_kospi": {"1900-01-01": 0.003, "2025-01-01": 0.0015, "2026-01-01": 0.002},
        }
        costs = CostModel.from_config(cfg)
        assert costs.sell_tax_rate(date(2024, 12, 31)) == 0.003
        assert costs.sell_tax_rate(pd.Timestamp("2025-06-01")) == 0.0015
        assert costs.sell_tax_rate(date(2026, 1, 1)) == 0.002
        assert CostModel.from_config(cfg, etf=True).sell_tax_rate(date(2026, 1, 1)) == 0.0

    def test_round_trip_costs(self):
        costs = CostModel(0.001, 0.01, ((date(1900, 1, 1), 0.002),))
        assert costs.buy_price(100) == pytest.approx(101)
        assert costs.buy_cash_out(10, 101) == pytest.approx(1011.01)
        assert costs.sell_cash_in(10, 99, date(2020, 1, 1)) == pytest.approx(990 * 0.997)


class TestPortfolio:
    def test_buy_limited_by_cash_and_averages_price(self):
        book = Portfolio(cash=1_000, costs=NO_COSTS)
        assert book.buy(DAYS[0], "A", 30, 100, "x") == 10
        book.cash = 500
        book.buy(DAYS[1], "A", 5, 200, "x")
        assert book.positions["A"].shares == 12
        assert book.positions["A"].avg_price == pytest.approx((10 * 100 + 2 * 200) / 12)

    def test_split_keeps_value(self):
        book = Portfolio(cash=0, costs=NO_COSTS)
        book.cash = 1_000
        book.buy(DAYS[0], "A", 10, 100, "x")
        book.apply_adjustment("A", 0.02)
        assert book.positions["A"].shares == pytest.approx(500)
        assert book.positions["A"].avg_price == pytest.approx(2)


class TestEngine:
    def test_signal_fills_next_day_open_with_slippage(self):
        closes = {"A": [100.0] * 10}
        opens = {"A": [100.0, 100.0, 105.0, *[100.0] * 7]}
        rsi = {"A": [50, 25, *[50] * 8]}
        costs = CostModel(0.0, 0.01, ((date(1900, 1, 1), 0.0),))
        result = _run(_inputs(closes, rsi, opens=opens), costs=costs)
        buy = result.fills[0]
        assert (buy.date, buy.side) == (DAYS[2], "buy")
        assert buy.price == pytest.approx(105 * 1.01)
        # max_position = 30% * 1,000,000, 1/3 분할 → 100,000 / 100(종가) = 1,000주
        assert buy.qty == 1000

    def test_take_profit_sells_half_next_day(self):
        closes = {"A": [100.0, 100.0, 100.0, 111.0, *[111.0] * 6]}
        rsi = {"A": [25, 50, 50, 50, *[50] * 6]}
        spec = StrategySpec("t", {**RSI_ONLY, "sell_ratio": 0.5})
        result = _run(_inputs(closes, rsi), spec=spec)
        sells = [f for f in result.fills if f.side == "sell"]
        assert sells[0].date == DAYS[4]
        assert sells[0].qty == 500
        assert sells[0].reason == "take_profit"

    def test_split_does_not_create_pnl(self):
        closes = {"A": [100.0, 100.0, 100.0, 2.0, 2.0, *[2.0] * 5]}
        factors = {"A": [1.0, 1.0, 1.0, 0.02, *[1.0] * 6]}
        rsi = {"A": [25, *[50] * 9]}
        result = _run(_inputs(closes, rsi, factors=factors))
        assert result.equity.iloc[-1] == pytest.approx(CONFIG.capital)
        assert all(f.side == "buy" for f in result.fills)

    def test_delisted_position_liquidated_at_last_close(self):
        closes = {"A": [100.0, 100.0, 100.0, 80.0, *[np.nan] * 6]}
        rsi = {"A": [25, 50, 50, 50, *[np.nan] * 6]}
        result = _run(_inputs(closes, rsi))
        sell = next(f for f in result.fills if f.side == "sell")
        assert (sell.date, sell.price, sell.reason) == (DAYS[4], 80.0, "delisted")
        assert result.equity.iloc[-1] == pytest.approx(CONFIG.capital - 1000 * 20)

    def test_regime_filter_blocks_entries(self):
        closes, rsi = {"A": [100.0] * 10}, {"A": [25] * 10}
        regime = [False] * 10
        spec = StrategySpec("t", RSI_ONLY, use_regime_filter=True)
        assert _run(_inputs(closes, rsi, regime=regime), spec=spec).fills == []

    def test_disclosure_veto_blocks_and_records(self):
        closes, rsi = {"A": [100.0] * 10}, {"A": [25] * 10}
        veto = {"A": [(DAYS[0], DAYS[9])]}
        spec = StrategySpec("t", RSI_ONLY, use_disclosure_veto=True)
        result = _run(_inputs(closes, rsi, veto=veto), spec=spec)
        assert result.fills == []
        assert len(result.blocked_by_veto) == 9  # 마지막 날은 결정하지 않음

    def test_year_end_dividend_credited(self):
        days = pd.bdate_range("2020-12-24", periods=6)
        closes, rsi = {"A": [100.0] * 6}, {"A": [25, *[50] * 5]}
        inputs = _inputs(closes, rsi, days=days, dividends={("A", 2020): 10.0})
        result = _run(inputs)
        assert result.dividends == pytest.approx(1000 * 10)

    def test_position_limit_stops_buying(self):
        closes, rsi = {"A": [100.0] * 10}, {"A": [25] * 10}
        result = _run(_inputs(closes, rsi))
        bought = sum(f.qty for f in result.fills if f.side == "buy")
        assert bought * 100 <= CONFIG.max_position_pct * CONFIG.capital + 1e-6

    def test_equal_weight_invests_all_members(self):
        closes = {"A": [100.0] * 10, "B": [50.0] * 10}
        rsi = {"A": [50] * 10, "B": [50] * 10}
        result = _run(_inputs(closes, rsi), spec=EqualWeightSpec())
        held = {f.code: f.qty for f in result.fills}
        assert held == {"A": 4975, "B": 9950}


class TestBaselines:
    def test_buy_and_hold_tracks_price(self):
        etf = pd.DataFrame({"open": [10.0, 11.0], "close": [10.0, 12.0]}, index=DAYS[:2])
        equity = buy_and_hold(etf, 1_000, NO_COSTS)
        assert equity.tolist() == [1_000, 1_200]

    def test_monthly_dca_spreads_capital(self):
        days = pd.bdate_range("2020-01-01", "2020-03-31")
        etf = pd.DataFrame({"open": 10.0, "close": 10.0}, index=days)
        equity, flows = monthly_dca(etf, 3_000, NO_COSTS)
        assert flows.tolist() == [1_000, 1_000, 1_000]
        assert equity.iloc[-1] == pytest.approx(3_000)
