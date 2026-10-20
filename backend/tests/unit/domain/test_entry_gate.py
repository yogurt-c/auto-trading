"""Unit tests for EntryGate and OrderSizer."""

import pytest

from app.domain.trading_strategy.services import EntryGate, OrderSizer, StrategyEvaluator
from app.domain.trading_strategy.value_objects import EvaluationResult, MarketData


def _result(entry_triggered: bool, signal_score: float | None) -> EvaluationResult:
    return EvaluationResult(
        ticker="005930",
        current_price=100.0,
        entry_triggered=entry_triggered,
        exit_triggered=False,
        conditions={},
        signal_score=signal_score,
    )


@pytest.fixture
def gate():
    return EntryGate()


class TestEntryGate:
    def test_no_entry_signal_is_not_allowed_without_reason(self, gate):
        decision = gate.apply({"entry_rsi_below": 30}, _result(False, 0.0), position_value=0)
        assert decision.entry_allowed is False
        assert decision.blocked_reason is None

    def test_single_condition_skips_score_gate(self, gate):
        decision = gate.apply({"entry_rsi_below": 30}, _result(True, 1.0), position_value=0)
        assert decision.entry_allowed is True

    def test_position_at_limit_blocks(self, gate):
        strategy = {"entry_rsi_below": 30, "max_position": 1_000_000}
        decision = gate.apply(strategy, _result(True, 1.0), position_value=1_000_000)
        assert decision.entry_allowed is False
        assert "포지션 한도" in decision.blocked_reason

    def test_position_below_limit_allowed(self, gate):
        strategy = {"entry_rsi_below": 30, "max_position": 1_000_000}
        decision = gate.apply(strategy, _result(True, 1.0), position_value=999_999)
        assert decision.entry_allowed is True

    def test_score_below_half_blocks_with_three_conditions(self, gate):
        strategy = {"entry_rsi_below": 30, "entry_volume_surge": 2.0, "entry_sma_cross": 20}
        decision = gate.apply(strategy, _result(True, 1 / 3), position_value=0)
        assert decision.entry_allowed is False
        assert "signal_score" in decision.blocked_reason

    def test_score_exactly_half_allowed(self, gate):
        strategy = {"entry_rsi_below": 30, "entry_volume_surge": 2.0}
        decision = gate.apply(strategy, _result(True, 0.5), position_value=0)
        assert decision.entry_allowed is True

    def test_gate_counts_configured_not_evaluated_conditions(self, gate):
        """RSI 데이터가 없어 평가된 조건이 1개뿐이어도 설정 조건이 3개면 score 게이트 적용."""
        strategy = {
            "entry_rsi_below": 30,
            "entry_price_drop_pct": -5.0,
            "entry_volume_surge": 2.0,
        }
        market = MarketData(
            ticker="X", current_price=90.0, high_30d=100.0, rsi_14=None, volume_ratio_20=1.0
        )
        result = StrategyEvaluator().evaluate(strategy, market, None)
        assert result.entry_triggered is True
        assert result.signal_score == pytest.approx(1 / 3, abs=1e-4)
        assert gate.apply(strategy, result, position_value=0).entry_allowed is False


@pytest.fixture
def sizer():
    return OrderSizer()


class TestOrderSizer:
    def test_buy_uses_one_third_of_max_position(self, sizer):
        assert sizer.buy_qty(3_000_000, 0, price=10_000, available_cash=10_000_000) == 100

    def test_buy_capped_by_remaining_limit(self, sizer):
        assert sizer.buy_qty(3_000_000, 2_500_000, price=10_000, available_cash=1e9) == 50

    def test_buy_capped_by_cash(self, sizer):
        assert sizer.buy_qty(3_000_000, 0, price=10_000, available_cash=305_000) == 30

    def test_buy_zero_when_price_exceeds_budget(self, sizer):
        assert sizer.buy_qty(30_000, 0, price=20_000, available_cash=1e9) == 0

    def test_buy_zero_when_over_limit(self, sizer):
        assert sizer.buy_qty(1_000_000, 1_200_000, price=1_000, available_cash=1e9) == 0

    @pytest.mark.parametrize(
        ("shares", "ratio", "expected"),
        [(10, 0.5, 5), (3, 0.5, 2), (1, 0.5, 1), (10, None, 10), (0, 0.5, 0), (7, 1.0, 7)],
    )
    def test_sell_qty_rounds_up(self, sizer, shares, ratio, expected):
        assert sizer.sell_qty(shares, ratio) == expected
