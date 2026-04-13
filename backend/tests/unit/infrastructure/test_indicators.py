"""기술지표 계산 함수 단위 테스트."""

from __future__ import annotations

import pandas as pd
import pytest

from app.infrastructure.indicators import (
    calc_atr,
    calc_bollinger,
    calc_disparity,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_sma,
    calc_volume_ratio,
)

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_closes(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


def _make_ohlcv(n: int, price: float = 100.0, volume: float = 1000.0):
    closes = pd.Series([price] * n, dtype=float)
    highs = pd.Series([price * 1.01] * n, dtype=float)
    lows = pd.Series([price * 0.99] * n, dtype=float)
    volumes = pd.Series([volume] * n, dtype=float)
    return closes, highs, lows, volumes


# ---------------------------------------------------------------------------
# calc_rsi
# ---------------------------------------------------------------------------


class TestCalcRsi:
    def test_returns_float_in_valid_range(self):
        closes = _make_closes([100 + i * 0.5 for i in range(30)])
        result = calc_rsi(closes)
        assert result is not None
        assert 0 <= result <= 100

    def test_insufficient_data_returns_none(self):
        closes = _make_closes([100.0] * 10)
        assert calc_rsi(closes, period=14) is None

    def test_all_gains_rsi_near_100(self):
        # 꾸준히 상승하면 RSI ≈ 100
        closes = _make_closes([float(i) for i in range(1, 40)])
        result = calc_rsi(closes)
        assert result is not None
        assert result > 90

    def test_all_losses_rsi_near_0(self):
        # 꾸준히 하락하면 RSI ≈ 0
        closes = _make_closes([float(40 - i) for i in range(40)])
        result = calc_rsi(closes)
        assert result is not None
        assert result < 10


# ---------------------------------------------------------------------------
# calc_sma
# ---------------------------------------------------------------------------


class TestCalcSma:
    def test_flat_series_equals_price(self):
        closes = _make_closes([100.0] * 30)
        assert calc_sma(closes, 20) == pytest.approx(100.0)

    def test_insufficient_data_returns_none(self):
        closes = _make_closes([100.0] * 10)
        assert calc_sma(closes, 20) is None

    def test_correct_average(self):
        closes = _make_closes(list(range(1, 11)))  # [1..10]
        result = calc_sma(closes, 5)
        assert result == pytest.approx(8.0)  # mean([6,7,8,9,10])


# ---------------------------------------------------------------------------
# calc_ema
# ---------------------------------------------------------------------------


class TestCalcEma:
    def test_returns_float_for_sufficient_data(self):
        closes = _make_closes([100.0] * 20)
        result = calc_ema(closes, 12)
        assert result is not None
        assert isinstance(result, float)

    def test_insufficient_data_returns_none(self):
        closes = _make_closes([100.0] * 5)
        assert calc_ema(closes, 12) is None


# ---------------------------------------------------------------------------
# calc_macd
# ---------------------------------------------------------------------------


class TestCalcMacd:
    def test_returns_three_values(self):
        closes = _make_closes([100.0 + i * 0.1 for i in range(60)])
        m, s, h = calc_macd(closes)
        assert all(v is not None for v in [m, s, h])

    def test_histogram_equals_macd_minus_signal(self):
        closes = _make_closes([100.0 + i * 0.1 for i in range(60)])
        m, s, h = calc_macd(closes)
        assert h == pytest.approx(m - s, abs=1e-6)

    def test_insufficient_data_returns_none_tuple(self):
        closes = _make_closes([100.0] * 20)
        assert calc_macd(closes) == (None, None, None)


# ---------------------------------------------------------------------------
# calc_bollinger
# ---------------------------------------------------------------------------


class TestCalcBollinger:
    def test_upper_gt_lower(self):
        closes = _make_closes([100.0 + (i % 5) for i in range(30)])
        upper, _middle, lower = calc_bollinger(closes)
        assert upper is not None
        assert lower is not None
        assert upper > lower

    def test_flat_series_bands_symmetric(self):
        closes = _make_closes([100.0] * 30)
        upper, _middle, lower = calc_bollinger(closes)
        # std=0이므로 upper==middle==lower
        assert upper == pytest.approx(100.0)
        assert lower == pytest.approx(100.0)

    def test_insufficient_data_returns_none_tuple(self):
        closes = _make_closes([100.0] * 10)
        assert calc_bollinger(closes) == (None, None, None)


# ---------------------------------------------------------------------------
# calc_disparity
# ---------------------------------------------------------------------------


class TestCalcDisparity:
    def test_flat_series_returns_zero(self):
        closes = _make_closes([100.0] * 30)
        result = calc_disparity(closes)
        assert result == pytest.approx(0.0)

    def test_price_above_sma_positive(self):
        # 끝에 큰 값을 넣으면 disparity 양수
        closes = _make_closes([100.0] * 19 + [110.0])
        result = calc_disparity(closes)
        assert result is not None
        assert result > 0

    def test_price_below_sma_negative(self):
        closes = _make_closes([100.0] * 19 + [90.0])
        result = calc_disparity(closes)
        assert result is not None
        assert result < 0


# ---------------------------------------------------------------------------
# calc_atr
# ---------------------------------------------------------------------------


class TestCalcAtr:
    def test_returns_positive_value(self):
        closes, highs, lows, _ = _make_ohlcv(30)
        result = calc_atr(highs, lows, closes)
        assert result is not None
        assert result > 0

    def test_insufficient_data_returns_none(self):
        closes, highs, lows, _ = _make_ohlcv(10)
        assert calc_atr(highs, lows, closes, period=14) is None


# ---------------------------------------------------------------------------
# calc_volume_ratio
# ---------------------------------------------------------------------------


class TestCalcVolumeRatio:
    def test_uniform_volume_returns_one(self):
        volumes = pd.Series([1000.0] * 30)
        result = calc_volume_ratio(volumes)
        assert result == pytest.approx(1.0)

    def test_double_volume_returns_two(self):
        # 직전 20개(period)는 1000, 마지막 1개(현재)는 2000 → ratio = 2.0
        # calc_volume_ratio는 volumes.iloc[-period-1:-1](직전 period개)를 평균으로 사용
        volumes = pd.Series([1000.0] * 25 + [2000.0])  # 26개: 직전20개=1000, 현재=2000
        result = calc_volume_ratio(volumes)
        assert result is not None
        assert result == pytest.approx(2.0)

    def test_insufficient_data_returns_none(self):
        volumes = pd.Series([1000.0] * 5)
        assert calc_volume_ratio(volumes, period=20) is None
