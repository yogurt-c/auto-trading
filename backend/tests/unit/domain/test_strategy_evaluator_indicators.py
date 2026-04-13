"""기술지표 기반 진입 조건 및 signal_score 테스트."""

from __future__ import annotations

import pytest

from app.domain.trading_strategy.services import StrategyEvaluator
from app.domain.trading_strategy.value_objects import MarketData

evaluator = StrategyEvaluator()


def _market_data(**kwargs) -> MarketData:
    defaults = {
        "ticker": "AAPL",
        "current_price": 100.0,
        "currency": "USD",
        "market": "US",
    }
    defaults.update(kwargs)
    return MarketData(**defaults)


def _strategy(**kwargs) -> dict:
    return kwargs


# ---------------------------------------------------------------------------
# entry_bb_lower_touch
# ---------------------------------------------------------------------------


class TestEntryBbLowerTouch:
    def test_triggered_when_price_below_bb_lower(self):
        mkt = _market_data(current_price=95.0, bb_lower=98.0)
        result = evaluator.evaluate(_strategy(entry_bb_lower_touch=True), mkt, None)
        assert result.conditions["entry_bb_lower_touch"]["triggered"] is True
        assert result.entry_triggered is True

    def test_not_triggered_when_price_above_bb_lower(self):
        mkt = _market_data(current_price=105.0, bb_lower=98.0)
        result = evaluator.evaluate(_strategy(entry_bb_lower_touch=True), mkt, None)
        assert result.conditions["entry_bb_lower_touch"]["triggered"] is False
        assert result.entry_triggered is False

    def test_skipped_when_bb_lower_is_none(self):
        mkt = _market_data(current_price=95.0, bb_lower=None)
        result = evaluator.evaluate(_strategy(entry_bb_lower_touch=True), mkt, None)
        assert "entry_bb_lower_touch" not in result.conditions

    def test_skipped_when_flag_is_false(self):
        mkt = _market_data(current_price=95.0, bb_lower=98.0)
        result = evaluator.evaluate(_strategy(entry_bb_lower_touch=False), mkt, None)
        assert "entry_bb_lower_touch" not in result.conditions


# ---------------------------------------------------------------------------
# entry_macd_hist_positive
# ---------------------------------------------------------------------------


class TestEntryMacdHistPositive:
    def test_triggered_when_hist_positive(self):
        mkt = _market_data(macd_hist=0.5)
        result = evaluator.evaluate(_strategy(entry_macd_hist_positive=True), mkt, None)
        assert result.conditions["entry_macd_hist_positive"]["triggered"] is True
        assert result.entry_triggered is True

    def test_not_triggered_when_hist_negative(self):
        mkt = _market_data(macd_hist=-0.3)
        result = evaluator.evaluate(_strategy(entry_macd_hist_positive=True), mkt, None)
        assert result.conditions["entry_macd_hist_positive"]["triggered"] is False

    def test_skipped_when_macd_hist_is_none(self):
        mkt = _market_data(macd_hist=None)
        result = evaluator.evaluate(_strategy(entry_macd_hist_positive=True), mkt, None)
        assert "entry_macd_hist_positive" not in result.conditions


# ---------------------------------------------------------------------------
# entry_disparity_below
# ---------------------------------------------------------------------------


class TestEntryDisparityBelow:
    def test_triggered_when_disparity_below_threshold(self):
        mkt = _market_data(disparity_20=-6.0)
        result = evaluator.evaluate(_strategy(entry_disparity_below=-5.0), mkt, None)
        assert result.conditions["entry_disparity_below"]["triggered"] is True

    def test_not_triggered_when_disparity_above_threshold(self):
        mkt = _market_data(disparity_20=-3.0)
        result = evaluator.evaluate(_strategy(entry_disparity_below=-5.0), mkt, None)
        assert result.conditions["entry_disparity_below"]["triggered"] is False

    def test_skipped_when_disparity_is_none(self):
        mkt = _market_data(disparity_20=None)
        result = evaluator.evaluate(_strategy(entry_disparity_below=-5.0), mkt, None)
        assert "entry_disparity_below" not in result.conditions


# ---------------------------------------------------------------------------
# entry_volume_surge
# ---------------------------------------------------------------------------


class TestEntryVolumeSurge:
    def test_triggered_when_volume_above_threshold(self):
        mkt = _market_data(volume_ratio_20=2.5)
        result = evaluator.evaluate(_strategy(entry_volume_surge=2.0), mkt, None)
        assert result.conditions["entry_volume_surge"]["triggered"] is True

    def test_not_triggered_when_volume_below_threshold(self):
        mkt = _market_data(volume_ratio_20=1.5)
        result = evaluator.evaluate(_strategy(entry_volume_surge=2.0), mkt, None)
        assert result.conditions["entry_volume_surge"]["triggered"] is False


# ---------------------------------------------------------------------------
# entry_sma_cross
# ---------------------------------------------------------------------------


class TestEntrySmaСross:
    def test_triggered_when_price_above_sma20(self):
        mkt = _market_data(current_price=105.0, sma_20=100.0)
        result = evaluator.evaluate(_strategy(entry_sma_cross=20), mkt, None)
        assert result.conditions["entry_sma_cross"]["triggered"] is True

    def test_not_triggered_when_price_below_sma20(self):
        mkt = _market_data(current_price=95.0, sma_20=100.0)
        result = evaluator.evaluate(_strategy(entry_sma_cross=20), mkt, None)
        assert result.conditions["entry_sma_cross"]["triggered"] is False

    def test_triggered_when_price_above_sma60(self):
        mkt = _market_data(current_price=110.0, sma_60=100.0)
        result = evaluator.evaluate(_strategy(entry_sma_cross=60), mkt, None)
        assert result.conditions["entry_sma_cross"]["triggered"] is True

    def test_skipped_when_sma_value_is_none(self):
        mkt = _market_data(current_price=105.0, sma_20=None)
        result = evaluator.evaluate(_strategy(entry_sma_cross=20), mkt, None)
        assert "entry_sma_cross" not in result.conditions


# ---------------------------------------------------------------------------
# signal_score
# ---------------------------------------------------------------------------


class TestSignalScore:
    def test_score_is_none_when_no_entry_conditions(self):
        mkt = _market_data()
        result = evaluator.evaluate(_strategy(), mkt, None)
        assert result.signal_score is None

    def test_score_is_1_when_all_triggered(self):
        mkt = _market_data(
            current_price=95.0,
            bb_lower=98.0,
            macd_hist=0.5,
        )
        strategy = _strategy(
            entry_bb_lower_touch=True,
            entry_macd_hist_positive=True,
        )
        result = evaluator.evaluate(strategy, mkt, None)
        assert result.signal_score == pytest.approx(1.0)

    def test_score_is_0_when_none_triggered(self):
        mkt = _market_data(
            current_price=105.0,
            bb_lower=98.0,
            macd_hist=-0.5,
        )
        strategy = _strategy(
            entry_bb_lower_touch=True,
            entry_macd_hist_positive=True,
        )
        result = evaluator.evaluate(strategy, mkt, None)
        assert result.signal_score == pytest.approx(0.0)

    def test_score_is_half_when_one_of_two_triggered(self):
        mkt = _market_data(
            current_price=95.0,
            bb_lower=98.0,  # triggered
            macd_hist=-0.5,  # not triggered
        )
        strategy = _strategy(
            entry_bb_lower_touch=True,
            entry_macd_hist_positive=True,
        )
        result = evaluator.evaluate(strategy, mkt, None)
        assert result.signal_score == pytest.approx(0.5)

    def test_score_range_valid(self):
        mkt = _market_data(
            current_price=95.0,
            bb_lower=98.0,
            macd_hist=0.3,
            disparity_20=-6.0,
        )
        strategy = _strategy(
            entry_bb_lower_touch=True,
            entry_macd_hist_positive=True,
            entry_disparity_below=-5.0,
        )
        result = evaluator.evaluate(strategy, mkt, None)
        assert result.signal_score is not None
        assert 0.0 <= result.signal_score <= 1.0
