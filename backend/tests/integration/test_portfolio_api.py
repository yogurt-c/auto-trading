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


def test_get_transactions(auth_client):
    """GET /api/portfolio/transactions → KIS 체결 주문 이력 반환 (KRW currency 주입)."""
    mock_orders = [
        {
            "id": "abc-123",
            "ticker": "AAPL",
            "action": "buy",
            "shares": 10.0,
            "price": 150.0,
            "total": 1500.0,
            "executed_at": "2026-03-18T10:30:00+09:00",
        }
    ]
    with patch("app.api.portfolio.kis_client.get_filled_orders", return_value=mock_orders):
        resp = auth_client.get("/api/portfolio/transactions")
    assert resp.status_code == 200
    data = resp.json()
    assert "transactions" in data
    assert "count" in data
    assert data["count"] == 1
    t = data["transactions"][0]
    assert t["id"] == "abc-123"
    assert t["ticker"] == "AAPL"
    assert t["action"] == "buy"
    assert t["shares"] == pytest.approx(10.0)
    assert t["price"] == pytest.approx(150.0)
    assert t["total"] == pytest.approx(1500.0)
    assert t["currency"] == "KRW"  # 국내 전용이므로 항상 KRW


def test_get_transactions_limit_param(auth_client):
    """GET /api/portfolio/transactions?limit=10 → limit 파라미터 수용."""
    with patch("app.api.portfolio.kis_client.get_filled_orders", return_value=[]) as mock_fn:
        resp = auth_client.get("/api/portfolio/transactions?limit=10")
    assert resp.status_code == 200
    mock_fn.assert_called_once_with(limit=10)


def test_get_transactions_alpaca_failure(auth_client):
    """Alpaca 오류 시 503 반환."""
    with patch(
        "app.api.portfolio.kis_client.get_filled_orders", side_effect=Exception("KIS error")
    ):
        resp = auth_client.get("/api/portfolio/transactions")
    assert resp.status_code == 503


def test_get_transactions_alpaca_key_missing(auth_client):
    """Alpaca API 키 미설정 시 400 반환."""
    with patch(
        "app.api.portfolio.kis_client.get_filled_orders", side_effect=ValueError("API 키 없음")
    ):
        resp = auth_client.get("/api/portfolio/transactions")
    assert resp.status_code == 400


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
