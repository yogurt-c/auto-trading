"""성과 지표·MarketData 사전 계산 테스트."""

import math

import numpy as np
import pandas as pd
import pytest

from app.infrastructure.indicators import build_market_data
from research.data.prices import add_adjustment
from research.market_data import compute_for_code, to_market_data
from research.metrics import (
    cagr,
    deflated_sharpe,
    max_drawdown,
    money_weighted_return,
    prob_sharpe_greater,
    sharpe,
    stationary_bootstrap_indices,
)


def _returns(seed: int, n: int = 750, mean: float = 0.0004, std: float = 0.01) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(mean, std, n), index=pd.bdate_range("2020-01-01", periods=n))


class TestBasicMetrics:
    def test_sharpe_annualizes(self):
        r = pd.Series([0.01, -0.005] * 50)
        expected = r.mean() / r.std(ddof=1) * math.sqrt(252)
        assert sharpe(r) == pytest.approx(expected)

    def test_sharpe_zero_volatility(self):
        assert sharpe(pd.Series([0.0] * 10)) == 0.0

    def test_max_drawdown(self):
        equity = pd.Series([100, 120, 90, 130, 65], dtype=float)
        assert max_drawdown(equity) == pytest.approx(-0.5)

    def test_cagr_doubling_in_one_year(self):
        idx = pd.DatetimeIndex(["2020-01-01", "2020-12-31"])
        equity = pd.Series([100.0, 200.0], index=idx)
        assert cagr(equity) == pytest.approx(1.0, abs=0.01)


class TestBootstrap:
    def test_indices_are_contiguous_blocks(self):
        idx = stationary_bootstrap_indices(100, 3, 20, np.random.default_rng(0))
        steps = np.diff(idx, axis=1)
        # 재시작이 아닌 위치는 다음 인덱스(+1, 끝에서는 0으로 순환)
        assert ((steps == 1) | (steps == -99)).mean() > 0.9

    def test_clearly_better_series_wins(self):
        a, b = _returns(1, mean=0.002), _returns(2, mean=-0.001)
        assert prob_sharpe_greater(a, b, reps=1000) > 0.95

    def test_identical_series_never_strictly_greater(self):
        a = _returns(3)
        assert prob_sharpe_greater(a, a, reps=200) == 0.0


class TestDeflatedSharpe:
    def test_more_trials_lowers_confidence(self):
        r = _returns(4, mean=0.001)
        few = deflated_sharpe(r, [0.5, 1.0])
        many = deflated_sharpe(r, list(np.linspace(-1.0, 2.0, 100)))
        assert 0 <= many < few <= 1

    def test_requires_multiple_trials(self):
        with pytest.raises(ValueError, match="2개 이상"):
            deflated_sharpe(_returns(5), [1.0])


def test_money_weighted_return_constant_growth():
    flows = pd.Series({pd.Timestamp("2020-01-01"): 100.0})
    mwr = money_weighted_return(flows, 110.0, pd.Timestamp("2020-12-31"))
    assert mwr == pytest.approx(0.1, abs=0.002)


class TestMarketDataPrecompute:
    def _panel(self, split_at: int | None) -> pd.DataFrame:
        n = 120
        prices = [100 + 10 * math.sin(i / 5) + i * 0.1 for i in range(n)]
        closes = [
            p / 50 if split_at is not None and i >= split_at else p for i, p in enumerate(prices)
        ]
        changes = [0.0] + [closes[i] - closes[i - 1] for i in range(1, n)]
        if split_at is not None:  # 분할일 전일대비는 기준가(직전 종가/50) 대비
            changes[split_at] = closes[split_at] - closes[split_at - 1] / 50
        return add_adjustment(
            pd.DataFrame(
                {
                    "date": pd.bdate_range("2020-01-01", periods=n),
                    "code": "005930",
                    "open": closes,
                    "high": closes,
                    "low": closes,
                    "close": closes,
                    "change": changes,
                    "volume": [
                        1000.0 * (50 if split_at and i >= split_at else 1) for i in range(n)
                    ],
                }
            )
        )

    def test_split_does_not_change_signals(self):
        no_split = compute_for_code(
            self._panel(None), pd.Timestamp("2020-01-01"), pd.Timestamp("2030-01-01")
        )
        split = compute_for_code(
            self._panel(80), pd.Timestamp("2020-01-01"), pd.Timestamp("2030-01-01")
        )
        last_plain, last_split = no_split[-1], split[-1]
        assert last_split["rsi_14"] == pytest.approx(last_plain["rsi_14"])
        assert last_split["volume_ratio_20"] == pytest.approx(last_plain["volume_ratio_20"])
        assert last_split["current_price"] == pytest.approx(last_plain["current_price"] / 50)
        # 분할 전날 판단은 분할 전 실제 가격 기준
        assert split[79]["current_price"] == pytest.approx(no_split[79]["current_price"])

    def test_matches_backend_build_market_data(self):
        panel = self._panel(None)
        rows = compute_for_code(panel, pd.Timestamp("2020-01-01"), pd.Timestamp("2030-01-01"))
        s = panel.set_index("date")
        expected = build_market_data(
            "005930", "KR", "KRW", s["high"], s["low"], s["close"], s["volume"]
        )
        assert to_market_data(rows[-1]) == expected
