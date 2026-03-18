"""Unit tests for StrategyEvaluator."""

import pytest

from domain.trading_strategy.services import StrategyEvaluator
from domain.trading_strategy.value_objects import MarketData


@pytest.fixture
def evaluator():
    return StrategyEvaluator()


def _strategy(**kwargs):
    base = {"id": 1, "ticker": "AAPL"}
    base.update(kwargs)
    return base


def test_entry_price_drop_triggered(evaluator):
    """drop_pct(-6%) <= threshold(-5%) → entry_triggered=True."""
    strategy = _strategy(entry_price_drop_pct=-5.0)
    market = MarketData(ticker="AAPL", current_price=94.0, high_30d=100.0)
    result = evaluator.evaluate(strategy, market, None)
    assert result.entry_triggered is True
    assert result.conditions["entry_price_drop"]["triggered"] is True
    assert result.conditions["entry_price_drop"]["current_drop_pct"] == pytest.approx(-6.0)


def test_entry_price_drop_not_triggered(evaluator):
    """drop_pct(-3%) > threshold(-5%) → entry_triggered=False."""
    strategy = _strategy(entry_price_drop_pct=-5.0)
    market = MarketData(ticker="AAPL", current_price=97.0, high_30d=100.0)
    result = evaluator.evaluate(strategy, market, None)
    assert result.entry_triggered is False
    assert result.conditions["entry_price_drop"]["triggered"] is False
    assert result.conditions["entry_price_drop"]["current_drop_pct"] == pytest.approx(-3.0)


def test_entry_rsi_triggered(evaluator):
    """rsi(25) <= threshold(30) → entry_triggered=True."""
    strategy = _strategy(entry_rsi_below=30.0)
    market = MarketData(ticker="AAPL", current_price=100.0, rsi_14=25.0)
    result = evaluator.evaluate(strategy, market, None)
    assert result.entry_triggered is True
    assert result.conditions["entry_rsi"]["triggered"] is True
    assert result.conditions["entry_rsi"]["current_rsi"] == pytest.approx(25.0)


def test_entry_rsi_not_triggered(evaluator):
    """rsi(35) > threshold(30) → entry_triggered=False."""
    strategy = _strategy(entry_rsi_below=30.0)
    market = MarketData(ticker="AAPL", current_price=100.0, rsi_14=35.0)
    result = evaluator.evaluate(strategy, market, None)
    assert result.entry_triggered is False
    assert result.conditions["entry_rsi"]["triggered"] is False


def test_take_profit_triggered(evaluator):
    """pnl_pct(25%) >= tp(20%) → exit_triggered=True."""
    strategy = _strategy(take_profit_pct=20.0)
    market = MarketData(ticker="AAPL", current_price=125.0)
    holding = {"ticker": "AAPL", "avg_price": 100.0}
    result = evaluator.evaluate(strategy, market, holding)
    assert result.exit_triggered is True
    assert result.conditions["take_profit"]["triggered"] is True
    assert result.current_pnl_pct == pytest.approx(25.0)


def test_stop_loss_triggered(evaluator):
    """pnl_pct(-15%) <= sl(-10%) → exit_triggered=True."""
    strategy = _strategy(stop_loss_pct=-10.0)
    market = MarketData(ticker="AAPL", current_price=85.0)
    holding = {"ticker": "AAPL", "avg_price": 100.0}
    result = evaluator.evaluate(strategy, market, holding)
    assert result.exit_triggered is True
    assert result.conditions["stop_loss"]["triggered"] is True
    assert result.current_pnl_pct == pytest.approx(-15.0)


def test_no_holding_skips_exit(evaluator):
    """holding=None → take_profit/stop_loss 미평가, note 포함."""
    strategy = _strategy(take_profit_pct=20.0, stop_loss_pct=-10.0)
    market = MarketData(ticker="AAPL", current_price=130.0)
    result = evaluator.evaluate(strategy, market, None)
    assert result.exit_triggered is False
    assert "take_profit" not in result.conditions
    assert "stop_loss" not in result.conditions
    assert result.note is not None
    assert result.holding_avg_price is None
    assert result.current_pnl_pct is None


def test_combined_conditions(evaluator):
    """entry_price_drop + take_profit 동시 평가."""
    strategy = _strategy(
        entry_price_drop_pct=-5.0,
        take_profit_pct=20.0,
        stop_loss_pct=-10.0,
    )
    # drop: (94-100)/100*100 = -6% → triggered
    # pnl: (94-75)/75*100 ≈ 25.3% → take_profit triggered
    market = MarketData(ticker="AAPL", current_price=94.0, high_30d=100.0)
    holding = {"ticker": "AAPL", "avg_price": 75.0}
    result = evaluator.evaluate(strategy, market, holding)
    assert result.entry_triggered is True
    assert result.exit_triggered is True
    assert result.current_pnl_pct is not None
    assert result.current_pnl_pct > 20.0
    assert result.conditions["entry_price_drop"]["current_drop_pct"] == pytest.approx(-6.0)
    assert result.conditions["take_profit"]["current_pnl_pct"] > 20.0
