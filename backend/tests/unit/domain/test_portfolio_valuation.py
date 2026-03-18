"""Unit tests for PortfolioValuationService."""

import pytest

from app.domain.portfolio.services import PortfolioValuationService


@pytest.fixture
def service():
    return PortfolioValuationService()


def test_single_holding_profit(service):
    holdings = [{"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0}]
    snap = service.calculate(holdings, {"AAPL": 120.0})
    hv = snap.holdings[0]
    assert hv.pnl.amount > 0
    assert hv.pnl_pct > 0
    assert hv.pnl.amount == pytest.approx(200.0)
    assert hv.pnl_pct == pytest.approx(20.0)


def test_single_holding_loss(service):
    holdings = [{"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0}]
    snap = service.calculate(holdings, {"AAPL": 80.0})
    hv = snap.holdings[0]
    assert hv.pnl.amount < 0
    assert hv.pnl_pct < 0
    assert hv.pnl.amount == pytest.approx(-200.0)
    assert hv.pnl_pct == pytest.approx(-20.0)


def test_multiple_holdings_totals(service):
    holdings = [
        {"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0},
        {"ticker": "MSFT", "shares": 5.0, "avg_price": 200.0},
    ]
    prices = {"AAPL": 110.0, "MSFT": 220.0}
    snap = service.calculate(holdings, prices)
    assert len(snap.holdings) == 2
    # AAPL: 10 * 110 = 1100, MSFT: 5 * 220 = 1100 → total = 2200
    assert snap.total_market_value.amount == pytest.approx(2200.0)
    # Cost: AAPL 1000 + MSFT 1000 = 2000
    assert snap.total_cost_basis.amount == pytest.approx(2000.0)
    assert snap.total_pnl.amount == pytest.approx(200.0)


def test_missing_price_fallback(service):
    """가격 없는 ticker → avg_price로 fallback, pnl=0."""
    holdings = [{"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0}]
    snap = service.calculate(holdings, {})  # no price for AAPL
    hv = snap.holdings[0]
    assert hv.current_price.amount == pytest.approx(100.0)
    assert hv.pnl.amount == pytest.approx(0.0)
    assert hv.pnl_pct == pytest.approx(0.0)


def test_empty_holdings(service):
    snap = service.calculate([], {})
    assert snap.holdings == []
    assert snap.total_market_value.amount == pytest.approx(0.0)
    assert snap.total_cost_basis.amount == pytest.approx(0.0)
    assert snap.total_pnl.amount == pytest.approx(0.0)
    assert snap.total_pnl_pct == pytest.approx(0.0)
