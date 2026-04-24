"""Integration tests for Portfolio API endpoints.

DB: real Alembic SQLite (data/test.db)
External: core.market.get_current_prices and core.kis_client are mocked.
"""

from unittest.mock import patch

import pytest


def test_get_portfolio_empty(auth_client):
    """Holdings 없을 때 → 빈 응답 반환."""
    with patch("app.api.portfolio.db.get_all_holdings", return_value=[]):
        resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["holdings"] == []
    assert data["count"] == 0
    assert data["summary"] == {"kr": None, "us": None}


def test_get_portfolio_with_holdings(auth_client):
    """Mock holdings + mock prices → P&L 포함 응답 (US 종목)."""
    holdings = [
        {"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0, "market": "US", "currency": "USD"}
    ]
    with (
        patch("app.api.portfolio.db.get_all_holdings", return_value=holdings),
        patch("app.api.portfolio.get_current_prices", return_value={"AAPL": 120.0}),
    ):
        resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    h = data["holdings"][0]
    assert h["ticker"] == "AAPL"
    assert h["shares"] == 10.0
    assert h["avg_price"] == pytest.approx(100.0)
    assert h["current_price"] == pytest.approx(120.0)
    assert h["market_value"] == pytest.approx(1200.0)
    assert h["cost_basis"] == pytest.approx(1000.0)
    assert h["pnl"] == pytest.approx(200.0)
    assert h["pnl_pct"] == pytest.approx(20.0)
    assert h["market"] == "US"
    assert h["currency"] == "USD"
    # summary는 us에 집계됨
    assert data["summary"]["kr"] is None
    assert data["summary"]["us"]["total_market_value"] == pytest.approx(1200.0)
    assert data["summary"]["us"]["total_cost_basis"] == pytest.approx(1000.0)
    assert data["summary"]["us"]["total_pnl"] == pytest.approx(200.0)
    assert data["summary"]["us"]["total_pnl_pct"] == pytest.approx(20.0)
    assert data["summary"]["us"]["currency"] == "USD"


def test_get_portfolio_kr_holding(auth_client):
    """국내 종목 보유 시 KR 분리 summary 반환."""
    holdings = [
        {
            "ticker": "005930",
            "shares": 10.0,
            "avg_price": 70000.0,
            "market": "KR",
            "currency": "KRW",
        }
    ]
    with (
        patch("app.api.portfolio.db.get_all_holdings", return_value=holdings),
        patch("app.api.portfolio.get_current_prices", return_value={"005930": 75000.0}),
    ):
        resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["us"] is None
    assert data["summary"]["kr"]["total_market_value"] == pytest.approx(750000.0)
    assert data["summary"]["kr"]["currency"] == "KRW"


def test_get_portfolio_failed_tickers(auth_client):
    """가격 조회 실패한 ticker는 failed_tickers에 포함, avg_price로 fallback."""
    holdings = [
        {"ticker": "UNKNOWN", "shares": 5.0, "avg_price": 50.0, "market": "US", "currency": "USD"}
    ]
    with (
        patch("app.api.portfolio.db.get_all_holdings", return_value=holdings),
        patch("app.api.portfolio.get_current_prices", return_value={}),
    ):
        resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "UNKNOWN" in data["failed_tickers"]
    # fallback: current_price == avg_price → pnl == 0
    assert data["holdings"][0]["pnl"] == pytest.approx(0.0)
    assert data["holdings"][0]["pnl_pct"] == pytest.approx(0.0)
    assert data["holdings"][0]["current_price"] == pytest.approx(50.0)


def test_get_portfolio_response_structure(auth_client):
    """응답에 필수 필드가 모두 포함되어 있는지 확인."""
    holdings = [
        {"ticker": "TSLA", "shares": 3.0, "avg_price": 200.0, "market": "US", "currency": "USD"}
    ]
    with (
        patch("app.api.portfolio.db.get_all_holdings", return_value=holdings),
        patch("app.api.portfolio.get_current_prices", return_value={"TSLA": 210.0}),
    ):
        resp = auth_client.get("/api/portfolio")
    data = resp.json()
    required_keys = {"holdings", "summary", "failed_tickers", "count"}
    assert required_keys <= data.keys()
    h = data["holdings"][0]
    holding_keys = {
        "ticker",
        "shares",
        "avg_price",
        "current_price",
        "market_value",
        "cost_basis",
        "pnl",
        "pnl_pct",
        "market",
        "currency",
    }
    assert holding_keys <= h.keys()
    # summary 구조 확인
    assert "kr" in data["summary"]
    assert "us" in data["summary"]


def test_get_holdings(auth_client, db_holding):
    """GET /api/portfolio/holdings → DB에서 holdings 목록 반환."""
    resp = auth_client.get("/api/portfolio/holdings")
    assert resp.status_code == 200
    data = resp.json()
    assert "holdings" in data
    assert "count" in data
    our_h = next(h for h in data["holdings"] if h["ticker"] == "TESTHOLD")
    assert our_h["shares"] == pytest.approx(8.0)
    assert our_h["avg_price"] == pytest.approx(200.0)


def test_get_transactions_empty(auth_client):
    """GET /api/portfolio/transactions → trade_logs 없을 때 빈 응답."""
    resp = auth_client.get("/api/portfolio/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert "count" in data
    assert data["count"] == 0
    assert data["transactions"] == []


def test_get_transactions_returns_filled_trade_logs(auth_client, app_client):
    """filled trade_log가 있으면 트랜잭션 목록에 포함된다."""
    from app.infrastructure import repository as db

    log = db.add_trade_log(
        ticker="AAPL",
        side="buy",
        qty=10.0,
        order_type="market",
        status="filled",
        filled_price=150.0,
        currency="USD",
        market="US",
    )

    resp = auth_client.get("/api/portfolio/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    tickers = [t["ticker"] for t in data["transactions"]]
    assert "AAPL" in tickers

    t = next(t for t in data["transactions"] if t["ticker"] == "AAPL")
    assert t["action"] == "buy"
    assert t["shares"] == pytest.approx(10.0)
    assert t["price"] == pytest.approx(150.0)
    assert t["currency"] == "USD"
    assert t["market"] == "US"
    assert "executed_at" in t


def test_get_transactions_market_filter(auth_client, app_client):
    """market 필터 파라미터로 KR/US 분리 조회 가능."""
    from app.infrastructure import repository as db

    db.add_trade_log(
        ticker="005930",
        side="sell",
        qty=5.0,
        order_type="market",
        status="filled",
        filled_price=75000.0,
        currency="KRW",
        market="KR",
    )
    db.add_trade_log(
        ticker="TSLA",
        side="sell",
        qty=2.0,
        order_type="market",
        status="filled",
        filled_price=300.0,
        currency="USD",
        market="US",
    )

    resp_kr = auth_client.get("/api/portfolio/transactions?market=KR")
    assert resp_kr.status_code == 200
    kr_data = resp_kr.json()
    assert all(t["market"] == "KR" for t in kr_data["transactions"])

    resp_us = auth_client.get("/api/portfolio/transactions?market=US")
    assert resp_us.status_code == 200
    us_data = resp_us.json()
    assert all(t["market"] == "US" for t in us_data["transactions"])


def test_sync_holdings_success(auth_client):
    """POST /api/portfolio/sync → KIS mock 성공."""
    mock_positions = [
        {"ticker": "AAPL", "qty": 5.0, "avg_entry_price": 150.0, "market": "US", "currency": "USD"}
    ]
    with patch("app.api.portfolio.kis_client.sync_positions", return_value=mock_positions):
        resp = auth_client.post("/api/portfolio/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["synced_count"] == 1
    assert any(h["ticker"] == "AAPL" for h in data["holdings"])


def test_sync_holdings_failure(auth_client):
    """POST /api/portfolio/sync → KIS 오류 시 503 반환."""
    with patch("app.api.portfolio.kis_client.sync_positions", side_effect=Exception("KIS error")):
        resp = auth_client.post("/api/portfolio/sync")
    assert resp.status_code == 503
