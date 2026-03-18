"""Integration tests for Portfolio API endpoints.

DB: real Alembic SQLite (data/test.db)
External: core.market.get_current_prices and core.alpaca_client are mocked.
"""

from unittest.mock import patch

import pytest


def test_get_portfolio_empty(app_client):
    """Holdings 없을 때 → 빈 응답 반환."""
    with patch("backend.api.portfolio.db.get_all_holdings", return_value=[]):
        resp = app_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert data["holdings"] == []
    assert data["count"] == 0
    assert data["summary"] == {}


def test_get_portfolio_with_holdings(app_client):
    """Mock holdings + mock prices → P&L 포함 응답."""
    holdings = [{"ticker": "AAPL", "shares": 10.0, "avg_price": 100.0}]
    with patch("backend.api.portfolio.db.get_all_holdings", return_value=holdings), \
         patch("api.portfolio.get_current_prices", return_value={"AAPL": 120.0}):
        resp = app_client.get("/api/portfolio")
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
    assert data["summary"]["total_market_value"] == pytest.approx(1200.0)
    assert data["summary"]["total_cost_basis"] == pytest.approx(1000.0)
    assert data["summary"]["total_pnl"] == pytest.approx(200.0)
    assert data["summary"]["total_pnl_pct"] == pytest.approx(20.0)


def test_get_portfolio_failed_tickers(app_client):
    """가격 조회 실패한 ticker는 failed_tickers에 포함, avg_price로 fallback."""
    holdings = [{"ticker": "UNKNOWN", "shares": 5.0, "avg_price": 50.0}]
    with patch("backend.api.portfolio.db.get_all_holdings", return_value=holdings), \
         patch("api.portfolio.get_current_prices", return_value={}):
        resp = app_client.get("/api/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "UNKNOWN" in data["failed_tickers"]
    # fallback: current_price == avg_price → pnl == 0
    assert data["holdings"][0]["pnl"] == pytest.approx(0.0)
    assert data["holdings"][0]["pnl_pct"] == pytest.approx(0.0)
    assert data["holdings"][0]["current_price"] == pytest.approx(50.0)


def test_get_portfolio_response_structure(app_client):
    """응답에 필수 필드가 모두 포함되어 있는지 확인."""
    holdings = [{"ticker": "TSLA", "shares": 3.0, "avg_price": 200.0}]
    with patch("backend.api.portfolio.db.get_all_holdings", return_value=holdings), \
         patch("api.portfolio.get_current_prices", return_value={"TSLA": 210.0}):
        resp = app_client.get("/api/portfolio")
    data = resp.json()
    required_keys = {"holdings", "summary", "failed_tickers", "count"}
    assert required_keys <= data.keys()
    h = data["holdings"][0]
    holding_keys = {"ticker", "shares", "avg_price", "current_price", "market_value", "cost_basis", "pnl", "pnl_pct"}
    assert holding_keys <= h.keys()


def test_get_holdings(app_client, db_holding):
    """GET /api/portfolio/holdings → DB에서 holdings 목록 반환."""
    resp = app_client.get("/api/portfolio/holdings")
    assert resp.status_code == 200
    data = resp.json()
    assert "holdings" in data
    assert "count" in data
    our_h = next(h for h in data["holdings"] if h["ticker"] == "TESTHOLD")
    assert our_h["shares"] == pytest.approx(8.0)
    assert our_h["avg_price"] == pytest.approx(200.0)


def test_get_transactions(app_client, db_holding):
    """GET /api/portfolio/transactions → 거래 내역 반환."""
    resp = app_client.get("/api/portfolio/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert "count" in data
    our_t = next(t for t in data["transactions"] if t["ticker"] == "TESTHOLD")
    assert our_t["action"] == "buy"
    assert our_t["shares"] == pytest.approx(8.0)
    assert our_t["price"] == pytest.approx(200.0)
    assert our_t["total"] == pytest.approx(1600.0)


def test_get_transactions_limit_param(app_client):
    """GET /api/portfolio/transactions?limit=10 → limit 파라미터 수용."""
    with patch("backend.api.portfolio.db.get_transactions", return_value=[]) as mock_txns:
        resp = app_client.get("/api/portfolio/transactions?limit=10")
    assert resp.status_code == 200
    mock_txns.assert_called_once_with(limit=10)


def test_sync_holdings_success(app_client):
    """POST /api/portfolio/sync → Alpaca mock 성공."""
    mock_positions = [{"ticker": "AAPL", "qty": 5.0, "avg_entry_price": 150.0}]
    with patch("backend.api.portfolio.alpaca_client.sync_positions", return_value=mock_positions):
        resp = app_client.post("/api/portfolio/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["synced_count"] == 1
    assert any(h["ticker"] == "AAPL" for h in data["holdings"])


def test_sync_holdings_failure(app_client):
    """POST /api/portfolio/sync → Alpaca 오류 시 503 반환."""
    with patch("backend.api.portfolio.alpaca_client.sync_positions", side_effect=Exception("Alpaca error")):
        resp = app_client.post("/api/portfolio/sync")
    assert resp.status_code == 503
