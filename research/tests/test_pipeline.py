"""학습·검증 파이프라인 전체를 합성 데이터로 끝까지 돌려 보는 스모크 테스트."""

import numpy as np
import pandas as pd
import pytest

from research.engine import MarketInputs, StrategySpec
from research.experiment import Lab, Period, forward_returns, tuning_specs, veto_decision
from research.inputs import regime_series, veto_windows
from research.pipeline import run_test, run_train

DAYS = pd.bdate_range("2011-06-01", "2026-09-30")
CODES = ["000010", "000020", "000030"]


@pytest.fixture(scope="module")
def inputs() -> MarketInputs:
    rng = np.random.default_rng(7)
    closes = pd.DataFrame(
        {c: 10_000 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, len(DAYS)))) for c in CODES},
        index=DAYS,
    ).round()
    opens = (closes.shift(1).fillna(closes) * (1 + rng.normal(0, 0.003, closes.shape))).round()
    market_data = {
        (code, day): {
            "ticker": code,
            "current_price": float(closes.at[day, code]),
            "rsi_14": float(rng.uniform(10, 90)),
            "volume_ratio_20": float(rng.lognormal(0, 0.5)),
        }
        for code in CODES
        for day in DAYS
    }
    index_closes = closes.mean(axis=1)
    veto = {"000010": [(DAYS[i], DAYS[i + 19]) for i in range(200, 3000, 120)]}
    return MarketInputs(
        opens=opens,
        closes=closes,
        factors=pd.DataFrame(1.0, index=DAYS, columns=CODES),
        market_data=market_data,
        universe=pd.DataFrame({"rebalance_date": DAYS[0], "code": CODES, "rank": [1, 2, 3]}),
        regime_ok=regime_series(index_closes, 200),
        veto_until=veto,
        dividends={(c, y): 100.0 for c in CODES for y in range(2012, 2027)},
        last_trade_date=dict.fromkeys(CODES, DAYS[-1]),
    )


@pytest.fixture(scope="module")
def lab(inputs) -> Lab:
    etf = pd.DataFrame({"open": inputs.closes.mean(axis=1), "close": inputs.closes.mean(axis=1)})
    return Lab(inputs, etf)


def test_train_then_test_produces_decision(inputs, lab):
    train = run_train(lab)
    assert set(train) >= {"benchmarks", "S0", "S1_regime", "S2_veto", "final", "train_gate"}
    assert train["tuning"]["trials"] == 36
    assert train["S2_veto"]["blocked_entries"] > 0

    stressed = Lab(inputs, lab.etf, slippage=0.002)
    result = run_test(lab, stressed, train)
    assert {"P1", "P2", "P3", "P4", "P5", "P6"} <= set(result["checks"])
    assert result["decision"] in {"adopt_strategy", "fallback_index_dca"}
    assert result["equity"]["strategy"].index[0] >= pd.Timestamp("2020-01-02")


def test_tuning_specs_cover_grid():
    specs = tuning_specs(StrategySpec("base", {}, use_regime_filter=True))
    assert len(specs) == 36
    assert all(s.use_regime_filter for s in specs)
    assert len({s.name for s in specs}) == 36


def test_forward_returns_from_next_open(inputs):
    day, code = DAYS[300], "000020"
    (ret,) = forward_returns(inputs, [(day, code)], days=20)
    expected = inputs.closes.at[DAYS[320], code] / inputs.opens.at[DAYS[301], code] - 1
    assert ret == pytest.approx(expected)


def test_veto_decision_reports_counts(inputs, lab):
    period = Period("train", pd.Timestamp("2012-01-02"), pd.Timestamp("2013-12-30"))
    s2 = lab.run(StrategySpec("s2", {"entry_rsi_below": 60.0}, use_disclosure_veto=True), period)
    implement, detail = veto_decision(inputs, s2)
    assert detail["blocked_entries"] == len(s2.blocked_by_veto) > 0
    assert isinstance(implement, bool)


def test_veto_windows_start_next_trading_day():
    days = pd.bdate_range("2020-01-01", periods=30)
    disclosures = pd.DataFrame(
        {
            "report_nm": ["주요사항보고서(유상증자결정)", "분기보고서"],
            "rcept_dt": ["20200103", "20200106"],
        }
    )
    windows = veto_windows(disclosures, days, ["유상증자결정"], block_days=5)
    assert windows == [(pd.Timestamp("2020-01-06"), pd.Timestamp("2020-01-10"))]


def test_regime_false_until_sma_available():
    closes = pd.Series(range(1, 11), index=pd.bdate_range("2020-01-01", periods=10), dtype=float)
    regime = regime_series(closes, 5)
    assert not regime.iloc[:4].any()
    assert regime.iloc[4:].all()


def test_veto_windows_skip_subsidiary_disclosures():
    days = pd.bdate_range("2020-01-01", periods=30)
    disclosures = pd.DataFrame(
        {"report_nm": ["유상증자결정(종속회사의주요경영사항)"], "rcept_dt": ["20200103"]}
    )
    assert veto_windows(disclosures, days, ["유상증자결정"], 5, exclude=["종속회사"]) == []
