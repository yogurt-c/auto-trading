"""Unit tests for StrategyValidator."""

import pytest

from app.domain.trading_strategy.services import StrategyValidator


@pytest.fixture
def validator():
    return StrategyValidator()


def _validate(validator, **kwargs):
    """Helper: call validate() with defaults for unspecified params."""
    defaults = dict(
        strategy_type="value",
        entry_price_drop_pct=None,
        entry_rsi_below=None,
        take_profit_pct=None,
        stop_loss_pct=None,
        sell_ratio=None,
        dca_amount_usd=None,
        dca_frequency_days=None,
        max_position_usd=None,
    )
    defaults.update(kwargs)
    return validator.validate(**defaults)


def test_entry_price_drop_positive(validator):
    """양수 entry_price_drop_pct → WARNING."""
    warnings = _validate(validator, entry_price_drop_pct=5.0)
    assert len(warnings) == 1
    assert "양수" in warnings[0].message


def test_rsi_out_of_range_zero(validator):
    """entry_rsi_below=0 → WARNING (0 이하)."""
    warnings = _validate(validator, entry_rsi_below=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "entry_rsi_below" in warnings[0].message


def test_rsi_out_of_range_hundred(validator):
    """entry_rsi_below=100 → WARNING (100 이상)."""
    warnings = _validate(validator, entry_rsi_below=100.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "entry_rsi_below" in warnings[0].message


def test_stop_loss_gte_take_profit(validator):
    """stop_loss_pct >= take_profit_pct → WARNING."""
    warnings = _validate(validator, stop_loss_pct=5.0, take_profit_pct=5.0)
    assert any("stop_loss" in w.message or "손절" in w.message for w in warnings)


def test_stop_loss_smaller_than_entry_drop(validator):
    """abs(stop_loss) < abs(entry_drop) → WARNING."""
    # abs(-3) < abs(-10): 손절이 너무 작음
    warnings = _validate(
        validator,
        entry_price_drop_pct=-10.0,
        take_profit_pct=20.0,
        stop_loss_pct=-3.0,
    )
    assert any("절대값" in w.message for w in warnings)


def test_sell_ratio_zero(validator):
    """sell_ratio=0 → WARNING (0 이하)."""
    warnings = _validate(validator, sell_ratio=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "sell_ratio" in warnings[0].message


def test_sell_ratio_exceeds_one(validator):
    """sell_ratio=1.5 → WARNING (1 초과)."""
    warnings = _validate(validator, sell_ratio=1.5)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "sell_ratio" in warnings[0].message


def test_dca_frequency_days_zero(validator):
    """dca_frequency_days=0 → WARNING."""
    warnings = _validate(validator, dca_frequency_days=0)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "dca_frequency_days" in warnings[0].message


def test_dca_frequency_days_negative(validator):
    """dca_frequency_days=-1 → WARNING."""
    warnings = _validate(validator, dca_frequency_days=-1)
    assert len(warnings) == 1
    assert warnings[0].severity == "warning"
    assert "dca_frequency_days" in warnings[0].message


def test_dca_amount_exceeds_max(validator):
    """dca_amount_usd(1000) > max_position_usd(500) → WARNING."""
    warnings = _validate(validator, dca_amount_usd=1000.0, max_position_usd=500.0)
    assert len(warnings) == 1


def test_dca_missing_amount(validator):
    """strategy_type=dca, dca_amount_usd=None → WARNING."""
    warnings = _validate(
        validator,
        strategy_type="dca",
        dca_amount_usd=None,
        dca_frequency_days=7,
    )
    assert any("dca_amount_usd" in w.message for w in warnings)


def test_dca_missing_frequency(validator):
    """strategy_type=dca, dca_frequency_days=None → WARNING."""
    warnings = _validate(
        validator,
        strategy_type="dca",
        dca_amount_usd=100.0,
        dca_frequency_days=None,
    )
    assert any("dca_frequency_days" in w.message for w in warnings)


def test_valid_params_no_warnings(validator):
    """정상 파라미터 → 빈 리스트."""
    warnings = _validate(
        validator,
        entry_price_drop_pct=-5.0,
        take_profit_pct=20.0,
        stop_loss_pct=-10.0,
        sell_ratio=0.5,
    )
    assert len(warnings) == 0


def test_valid_dca_no_warnings(validator):
    """유효한 DCA 파라미터 → 빈 리스트."""
    warnings = _validate(
        validator,
        strategy_type="dca",
        dca_amount_usd=100.0,
        dca_frequency_days=7,
        max_position_usd=1000.0,
    )
    assert len(warnings) == 0
