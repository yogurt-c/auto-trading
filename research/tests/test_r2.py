"""R2 후보 전략 테스트 — 합성 시세로 체결·과세·신호 시점·합성 ETF 시차를 검증."""

from datetime import date

import pandas as pd
import pytest

from research.costs import CostModel
from research.data.assets import (
    leveraged_index,
    remove_spikes,
    synthetic_krw_etf,
    us_signal_series,
)
from research.engine import Engine, EngineConfig, MarketInputs, MomentumSpec
from research.r2 import (
    above_sma,
    dual_momentum_targets,
    fixed_mix_targets,
    month_end_days,
    trend_targets,
)
from research.rotation import AssetCosts, run_breakout, run_rotation

DAYS = pd.bdate_range("2020-01-27", periods=10)  # 1월 말을 포함
FREE = AssetCosts(0.0, 0.0)


def _ohlc(closes: list[float], opens: list[float] | None = None, days=DAYS) -> pd.DataFrame:
    opens = opens or closes
    return pd.DataFrame(
        {
            "open": opens,
            "high": [max(o, c) for o, c in zip(opens, closes, strict=True)],
            "low": [min(o, c) for o, c in zip(opens, closes, strict=True)],
            "close": closes,
        },
        index=days,
    )


class TestRotation:
    def test_target_executes_next_open(self):
        prices = {"a": _ohlc([100] * 2 + [200] * 8, opens=[100, 150] + [200] * 8)}
        result = run_rotation(
            "t", prices, {DAYS[0]: {"a": 1.0}}, DAYS, 1_000, {"a": FREE}, cash_buffer=0.0
        )
        # 1일차 종가 100으로 10주 결정 → 2일차 시가 150이라 현금 1,000으로 6주만 체결
        assert result.trade_log == [(DAYS[1], "a", "buy", 6, 150.0)]
        assert result.equity.iloc[-1] == pytest.approx(100 + 6 * 200)

    def test_gain_tax_only_on_profitable_sale(self):
        prices = {"a": _ohlc([100, 100, 200, 200, 200, 50, 50, 50, 50, 50])}
        taxed = {"a": AssetCosts(0.0, 0.0, gain_tax_rate=0.154)}
        targets = {DAYS[0]: {"a": 1.0}, DAYS[2]: {}, DAYS[3]: {"a": 1.0}, DAYS[4]: {}}
        result = run_rotation("t", prices, targets, DAYS, 1_000, taxed, cash_buffer=0.0)
        # 100에 10주 → 200에 매도: 이익 1,000에 154 과세 → 1,846
        # 200에 9주 재매수 → 50에 매도: 손실은 앞선 과세와 통산하지 않음 → 46 + 450
        assert result.taxes == pytest.approx(154.0)
        assert result.equity.iloc[-1] == pytest.approx(496.0)

    def test_exempt_asset_has_no_tax(self):
        prices = {"a": _ohlc([100, 100, 200] + [200] * 7)}
        targets = {DAYS[0]: {"a": 1.0}, DAYS[2]: {}}
        result = run_rotation("t", prices, targets, DAYS, 1_000, {"a": FREE}, cash_buffer=0.0)
        assert result.taxes == 0.0
        assert result.equity.iloc[-1] == pytest.approx(2_000)

    def test_switch_sells_before_buying(self):
        prices = {"a": _ohlc([100] * 10), "b": _ohlc([50] * 10)}
        targets = {DAYS[0]: {"a": 1.0}, DAYS[3]: {"b": 1.0}}
        result = run_rotation(
            "t", prices, targets, DAYS, 1_000, {"a": FREE, "b": FREE}, cash_buffer=0.0
        )
        assert [(d, a, s) for d, a, s, _, _ in result.trade_log] == [
            (DAYS[1], "a", "buy"),
            (DAYS[4], "a", "sell"),
            (DAYS[4], "b", "buy"),
        ]


class TestBreakout:
    def test_buys_at_target_and_sells_next_open(self):
        df = pd.DataFrame(
            {
                "open": [100, 100, 104, 104],
                "high": [110, 108, 106, 106],
                "low": [100, 99, 103, 103],
                "close": [105, 107, 105, 105],
            },
            index=DAYS[:4],
        )
        # 2일차 목표가 = 100 + 0.5*(110-100) = 105, 고가 108 ≥ 105 → 105에 매수
        result = run_breakout("t", df, DAYS[1:4], 1_050, FREE, k=0.5)
        assert result.trade_log[0] == (DAYS[1], "x", "buy", 10, 105.0)
        assert result.trade_log[1] == (DAYS[2], "x", "sell", 10, 104.0)

    def test_no_trade_below_target(self):
        df = pd.DataFrame(
            {"open": [100, 100, 100], "high": [110, 104, 104], "low": [100, 98, 98]},
            index=DAYS[:3],
        ).assign(close=100)
        result = run_breakout("t", df, DAYS[1:3], 1_000, FREE, k=0.5)
        assert result.trade_log == []
        assert result.equity.tolist() == [1_000, 1_000]

    def test_no_entry_on_last_day(self):
        df = pd.DataFrame(
            {"open": [100, 100], "high": [110, 120], "low": [100, 100], "close": [100, 115]},
            index=DAYS[:2],
        )
        assert run_breakout("t", df, DAYS[1:2], 1_000, FREE, k=0.5).trade_log == []


class TestSignals:
    def test_month_end_days(self):
        assert list(month_end_days(DAYS)) == [pd.Timestamp("2020-01-31"), DAYS[-1]]

    def test_above_sma_false_until_window_full(self):
        s = pd.Series([1.0, 2.0, 3.0, 2.0], index=DAYS[:4])
        assert above_sma(s, 3).tolist() == [False, False, True, False]

    def test_trend_targets_switch_on_state_change_and_month_end(self):
        risk_on = {"x": pd.Series([True, True, False, False] + [True] * 6, index=DAYS)}
        sleeves = [{"weight": 1.0, "risk_on": "lev", "risk_off": "bond", "signal_index": "x"}]
        targets = trend_targets(sleeves, risk_on, DAYS)
        assert targets[DAYS[0]] == {"lev": 1.0}
        assert targets[DAYS[2]] == {"bond": 1.0}
        assert targets[DAYS[4]] == {"lev": 1.0}  # 2020-01-31 월말이자 상태 변경
        assert DAYS[1] not in targets

    def test_trend_targets_merge_sleeves_on_same_asset(self):
        risk_on = {"x": pd.Series(False, index=DAYS), "y": pd.Series(False, index=DAYS)}
        sleeves = [
            {"weight": 0.5, "risk_on": "a", "risk_off": "bond", "signal_index": "x"},
            {"weight": 0.5, "risk_on": "b", "risk_off": "bond", "signal_index": "y"},
        ]
        assert trend_targets(sleeves, risk_on, DAYS)[DAYS[0]] == {"bond": 1.0}

    def test_dual_momentum_picks_best_or_safe(self):
        prices = {
            "kr": _ohlc([100, 100, 110, 110, 110, 110, 110, 110, 110, 110]),
            "us": _ohlc([100, 100, 105, 105, 90, 90, 90, 90, 90, 90]),
            "bond": _ohlc([100, 100, 101, 101, 120, 120, 120, 120, 120, 120]),
        }
        targets = dual_momentum_targets(prices, ["kr", "us"], "bond", 2, DAYS[2:])
        assert targets[DAYS[2]] == {"kr": 1.0}  # 기간 첫날: kr 10% > us 5% > 채권 1%
        assert targets[pd.Timestamp("2020-01-31")] == {"bond": 1.0}  # kr 0%, us -14%, 채권 19%

    def test_fixed_mix(self):
        targets = fixed_mix_targets({"a": 0.5, "b": 0.5}, DAYS)
        assert set(targets) == {DAYS[0], pd.Timestamp("2020-01-31"), DAYS[-1]}


class TestSyntheticAssets:
    def test_leveraged_index_without_costs(self):
        tr = pd.Series([100.0, 110.0, 99.0], index=DAYS[:3])
        rate = pd.Series(0.0, index=DAYS[:3])
        lev = leveraged_index(tr, rate, leverage=2, annual_drag=0.0)
        assert lev.tolist() == pytest.approx([1.0, 1.2, 1.2 * 0.8])

    def test_leveraged_index_pays_financing(self):
        tr = pd.Series([100.0, 100.0], index=DAYS[:2])
        rate = pd.Series(25.2, index=DAYS[:2])  # 연 25.2% → 일 0.1%
        assert leveraged_index(tr, rate, 2, 0.0).iloc[-1] == pytest.approx(0.999)

    def test_krw_price_uses_us_close_before_kr_day(self):
        us = pd.Series([10.0, 20.0], index=pd.to_datetime(["2020-01-06", "2020-01-07"]))
        fx = pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-06", "2020-01-07"]))
        cal = pd.to_datetime(["2020-01-07", "2020-01-08"])
        out = synthetic_krw_etf(us, fx, pd.DatetimeIndex(cal), base=1.0)
        # 1/7 한국: 1/6 미국 종가·환율(10*1), 1/8 한국: 1/7 값(20*2) → 4배
        assert out["close"].tolist() == pytest.approx([1.0, 4.0])
        assert (out["open"] == out["close"]).all()

    def test_us_signal_series_has_no_same_day_value(self):
        s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2020-01-06", "2020-01-07"]))
        out = us_signal_series(s, pd.DatetimeIndex(pd.to_datetime(["2020-01-06", "2020-01-08"])))
        assert pd.isna(out.iloc[0])
        assert out.iloc[1] == 2.0

    def test_remove_single_day_spike(self):
        df = _ohlc([100, 100, 114, 100, 101], days=DAYS[:5])
        cleaned = remove_spikes(df)
        assert cleaned["close"].tolist() == [100, 100, 100, 100, 101]

    def test_keeps_real_move(self):
        df = _ohlc([100, 100, 114, 115, 116], days=DAYS[:5])
        assert remove_spikes(df)["close"].tolist() == [100, 100, 114, 115, 116]


class TestMomentumEngine:
    def _inputs(self, closes: dict[str, list[float]], days: pd.DatetimeIndex) -> MarketInputs:
        close_df = pd.DataFrame(closes, index=days)
        return MarketInputs(
            opens=close_df,
            closes=close_df,
            factors=pd.DataFrame(1.0, index=days, columns=close_df.columns),
            market_data={},
            universe=pd.DataFrame(
                {"rebalance_date": days[0] - pd.Timedelta(days=1), "code": list(closes), "rank": 1}
            ),
            regime_ok=pd.Series(dtype=bool),
            veto_until={},
            dividends={},
            last_trade_date=dict.fromkeys(closes, days[-1]),
        )

    def test_holds_top_momentum_and_rotates(self):
        days = pd.bdate_range("2020-01-01", periods=8)
        inputs = self._inputs(
            {
                "a": [100, 110, 120, 120, 120, 120, 120, 120],
                "b": [100, 100, 100, 100, 150, 200, 200, 200],
            },
            days,
        )
        costs = CostModel(0.0, 0.0, ((date(1900, 1, 1), 0.0),))
        engine = Engine(inputs, EngineConfig(10_000, 1.0, 0.0), costs)
        spec = MomentumSpec("m", lookback=2, hold=1, every=3, cash_buffer=0.0)
        result = engine.run(spec, days[0], days[-1])
        held = [(f.date, f.code, f.side) for f in result.fills]
        # day0: 모멘텀 없음 → 주문 없음. day3: a 20% vs b 0% → a. day6: b 100% vs a 0% → b
        assert held[0] == (days[4], "a", "buy")
        assert (days[7], "a", "sell") in held
        assert (days[7], "b", "buy") in held

    def test_split_adjusted_momentum(self):
        days = pd.bdate_range("2020-01-01", periods=5)
        inputs = self._inputs({"a": [100, 100, 50, 50, 50], "b": [100, 100, 99, 99, 99]}, days)
        factors = inputs.factors.copy()
        factors.loc[days[2], "a"] = 0.5  # 2:1 분할 — 실제 수익률 0%
        inputs = MarketInputs(**{**inputs.__dict__, "factors": factors})
        costs = CostModel(0.0, 0.0, ((date(1900, 1, 1), 0.0),))
        engine = Engine(inputs, EngineConfig(10_000, 1.0, 0.0), costs)
        result = engine.run(MomentumSpec("m", 2, 1, 2, 0.0), days[0], days[-1])
        # day2 판단: a 0% (분할 조정) vs b -1% → a
        assert result.fills[0].code == "a"


class TestR3Stats:
    def test_longest_recovery_counts_until_new_high(self):
        from research.r3 import longest_recovery_days

        days = pd.to_datetime(["2020-01-01", "2020-01-11", "2020-01-31", "2020-02-10"])
        equity = pd.Series([100, 80, 100, 90], index=days)
        # 1/1 고점 → 1/31 회복: 30일. 1/31 고점 → 끝(2/10) 미회복: 10일
        assert longest_recovery_days(equity) == 30

    def test_unrecovered_drawdown_runs_to_end(self):
        from research.r3 import longest_recovery_days

        days = pd.to_datetime(["2020-01-01", "2020-03-01"])
        assert longest_recovery_days(pd.Series([100, 50], index=days)) == 60

    def test_leveraged_index_fills_monthly_rate(self):
        tr = pd.Series(
            [100.0, 100.0, 100.0], index=pd.to_datetime(["2020-01-02", "2020-01-03", "2020-02-03"])
        )
        rate = pd.Series([25.2], index=pd.to_datetime(["2020-01-01"]))  # 월초(휴일) 값 하나
        lev = leveraged_index(tr, rate, 2, 0.0)
        assert lev.iloc[-1] == pytest.approx(0.999**2)


class TestBondProxy:
    def test_carry_and_duration(self):
        from research.r4 import bond_proxy

        rate = pd.Series(
            [12.0, 12.0, 13.0], index=pd.to_datetime(["2020-01-01", "2020-02-01", "2020-03-01"])
        )
        cal = pd.DatetimeIndex(
            pd.to_datetime(["2020-01-02", "2020-02-03", "2020-02-04", "2020-03-02"])
        )
        out = bond_proxy(rate, cal, duration=2.0, annual_drag=0.0)["close"]
        # 1월: 전월 금리 없음 → 0. 2월: 12%/12 = 1% (이틀에 나눔). 3월: 1% - 2 * 1%p = -1%
        assert out.iloc[0] == pytest.approx(10_000)
        assert out.iloc[2] == pytest.approx(10_100)
        assert out.iloc[3] == pytest.approx(10_100 * 0.99)
