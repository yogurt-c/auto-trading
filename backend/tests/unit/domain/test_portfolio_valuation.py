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
    # market/currency 기본값 적용 → US/USD
    assert hv.market == "US"
    assert hv.currency == "USD"


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
    # 모두 US(기본값) → snap.us에 집계됨
    assert snap.us is not None
    assert snap.kr is None
    # AAPL: 10 * 110 = 1100, MSFT: 5 * 220 = 1100 → total = 2200
    assert snap.us.total_market_value.amount == pytest.approx(2200.0)
    # Cost: AAPL 1000 + MSFT 1000 = 2000
    assert snap.us.total_cost_basis.amount == pytest.approx(2000.0)
    assert snap.us.total_pnl.amount == pytest.approx(200.0)


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
    assert snap.kr is None
    assert snap.us is None


def test_kr_us_split(service):
    """국내·해외 혼합 보유 시 KR/US 분리 집계."""
    holdings = [
        {"ticker": "005930", "shares": 10.0, "avg_price": 70000.0, "market": "KR", "currency": "KRW"},
        {"ticker": "AAPL", "shares": 5.0, "avg_price": 150.0, "market": "US", "currency": "USD"},
    ]
    snap = service.calculate(holdings, {"005930": 75000.0, "AAPL": 160.0})

    assert snap.kr is not None
    assert snap.us is not None
    assert snap.kr.market == "KR"
    assert snap.kr.currency == "KRW"
    assert snap.us.market == "US"
    assert snap.us.currency == "USD"
    assert snap.kr.total_market_value.amount == pytest.approx(750000.0)
    assert snap.kr.total_cost_basis.amount == pytest.approx(700000.0)
    assert snap.kr.total_pnl.amount == pytest.approx(50000.0)
    assert snap.us.total_market_value.amount == pytest.approx(800.0)
    assert snap.us.total_cost_basis.amount == pytest.approx(750.0)
    assert snap.us.total_pnl.amount == pytest.approx(50.0)
    assert snap.kr.holding_count == 1
    assert snap.us.holding_count == 1


def test_kr_only(service):
    """국내 종목만 보유 → kr만 존재, us는 None."""
    holdings = [
        {"ticker": "005930", "shares": 10.0, "avg_price": 70000.0, "market": "KR", "currency": "KRW"}
    ]
    snap = service.calculate(holdings, {"005930": 75000.0})
    assert snap.kr is not None
    assert snap.us is None
    assert snap.kr.total_market_value.amount == pytest.approx(750000.0)


def test_us_only_with_explicit_market(service):
    """해외 종목만 보유 (명시적) → us만 존재, kr는 None."""
    holdings = [
        {"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0, "market": "US", "currency": "USD"}
    ]
    snap = service.calculate(holdings, {"AAPL": 120.0})
    assert snap.us is not None
    assert snap.kr is None
    assert snap.us.total_pnl.amount == pytest.approx(200.0)
