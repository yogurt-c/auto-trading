"""Unit tests for StrategyValidator."""

import pytest

from app.domain.trading_strategy.services import StrategyValidator


@pytest.fixture
def validator():
    return StrategyValidator()


def _validate(validator, **kwargs):
    """Helper: call validate() with defaults for unspecified params."""
    defaults = {
        "strategy_type": "value",
        "entry_price_drop_pct": None,
        "entry_rsi_below": 30.0,  # "진입 조건 없음" WARNING 방지용 기본값
        "take_profit_pct": None,
        "stop_loss_pct": None,
        "sell_ratio": None,
        "dca_amount": None,
        "dca_frequency_days": None,
        "max_position": None,
    }
    defaults.update(kwargs)
    return validator.validate(**defaults)


def test_entry_price_drop_positive(validator):
    """양수 entry_price_drop_pct → ERROR (하락 조건은 음수여야 함)."""
    warnings = _validate(validator, entry_price_drop_pct=5.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "0 이상" in warnings[0].message


def test_entry_price_drop_zero(validator):
    """entry_price_drop_pct=0.0 → ERROR (0이면 항상 트리거됨)."""
    warnings = _validate(validator, entry_price_drop_pct=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_rsi_out_of_range_zero(validator):
    """entry_rsi_below=0 → ERROR (0 이하, 저장 차단)."""
    warnings = _validate(validator, entry_rsi_below=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "entry_rsi_below" in warnings[0].message


def test_rsi_out_of_range_hundred(validator):
    """entry_rsi_below=100 → ERROR (100 이상, 항상 트리거됨)."""
    warnings = _validate(validator, entry_rsi_below=100.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "entry_rsi_below" in warnings[0].message


def test_stop_loss_gte_take_profit(validator):
    """stop_loss_pct >= take_profit_pct → ERROR (논리적 모순)."""
    warnings = _validate(validator, stop_loss_pct=5.0, take_profit_pct=5.0)
    assert any("stop_loss" in w.message or "손절" in w.message for w in warnings)
    assert any(w.severity == "error" for w in warnings)


def test_sell_ratio_zero(validator):
    """sell_ratio=0 → ERROR (0 이하, 실행 불가)."""
    warnings = _validate(validator, sell_ratio=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "sell_ratio" in warnings[0].message


def test_sell_ratio_exceeds_one(validator):
    """sell_ratio=1.5 → ERROR (1 초과, 보유량 초과 매도)."""
    warnings = _validate(validator, sell_ratio=1.5)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "sell_ratio" in warnings[0].message


def test_dca_frequency_days_zero(validator):
    """dca_frequency_days=0 → ERROR (실행 불가)."""
    warnings = _validate(validator, dca_frequency_days=0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "dca_frequency_days" in warnings[0].message


def test_dca_frequency_days_negative(validator):
    """dca_frequency_days=-1 → ERROR (실행 불가)."""
    warnings = _validate(validator, dca_frequency_days=-1)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "dca_frequency_days" in warnings[0].message


def test_dca_amount_exceeds_max(validator):
    """dca_amount(1000) > max_position(500) → ERROR (첫 매수부터 한도 초과)."""
    warnings = _validate(validator, dca_amount=1000.0, max_position=500.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_dca_missing_amount(validator):
    """strategy_type=dca, dca_amount=None → ERROR (필수값 누락)."""
    warnings = _validate(
        validator,
        strategy_type="dca",
        dca_amount=None,
        dca_frequency_days=7,
    )
    assert any("dca_amount" in w.message for w in warnings)
    assert any(w.severity == "error" for w in warnings)


def test_dca_missing_frequency(validator):
    """strategy_type=dca, dca_frequency_days=None → ERROR (필수값 누락)."""
    warnings = _validate(
        validator,
        strategy_type="dca",
        dca_amount=100.0,
        dca_frequency_days=None,
    )
    assert any("dca_frequency_days" in w.message for w in warnings)
    assert any(w.severity == "error" for w in warnings)


def test_entry_sma_cross_unsupported(validator):
    """entry_sma_cross=30 → ERROR (평가기 지원 안 함)."""
    warnings = _validate(validator, entry_sma_cross=30)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"
    assert "entry_sma_cross" in warnings[0].message


def test_entry_price_drop_positive_is_error(validator):
    """entry_price_drop_pct 양수 → ERROR (저장 차단, 역전 전략 방지)."""
    warnings = _validate(validator, entry_price_drop_pct=5.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_entry_disparity_positive_is_error(validator):
    """entry_disparity_below 양수 → ERROR (저장 차단, 역전 전략 방지)."""
    warnings = _validate(validator, entry_disparity_below=3.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_entry_disparity_zero_is_error(validator):
    """entry_disparity_below=0.0 → ERROR (0이면 항상 트리거됨)."""
    warnings = _validate(validator, entry_disparity_below=0.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_entry_volume_surge_at_one_is_error(validator):
    """entry_volume_surge=1.0 → ERROR (평균 거래량 이하면 급등 아님)."""
    warnings = _validate(validator, entry_volume_surge=1.0)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_entry_volume_surge_below_one_is_error(validator):
    """entry_volume_surge=0.5 → ERROR (평균의 절반, 논리 역전)."""
    warnings = _validate(validator, entry_volume_surge=0.5)
    assert len(warnings) == 1
    assert warnings[0].severity == "error"


def test_stop_loss_smaller_than_entry_drop_is_warning(validator):
    """abs(stop_loss) < abs(entry_drop) → WARNING (비효율적이지만 유효)."""
    warnings = _validate(
        validator,
        entry_price_drop_pct=-10.0,
        take_profit_pct=20.0,
        stop_loss_pct=-3.0,
    )
    assert any("절대값" in w.message for w in warnings)
    assert all(w.severity == "warning" for w in warnings)


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
        dca_amount=100.0,
        dca_frequency_days=7,
        max_position=1000.0,
    )
    assert len(warnings) == 0
