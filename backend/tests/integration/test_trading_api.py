"""Integration tests for Trading API endpoints.

DB: real Alembic SQLite (data/test.db)
External: core.alpaca_client is mocked.
"""

from unittest.mock import patch

import pytest

_MOCK_ACCOUNT = {
    "cash": 10000.0,
    "portfolio_value": 15000.0,
    "buying_power": 10000.0,
    "currency": "USD",
    "status": "ACTIVE",
}

_MOCK_ORDER = {
    "alpaca_id": "test-order-id-123",
    "ticker": "AAPL",
    "side": "buy",
    "qty": 1.0,
    "order_type": "market",
    "status": "filled",
    "limit_price": None,
    "filled_avg_price": 150.0,
}


def test_get_account_success(auth_client):
    """GET /api/trading/account → Alpaca mock 성공 응답."""
    with patch("app.api.trading.alpaca_client.get_account", return_value=_MOCK_ACCOUNT), \
         patch("app.api.trading.alpaca_client.get_positions", return_value=[]):
        resp = auth_client.get("/api/trading/account")
    assert resp.status_code == 200
    data = resp.json()
    assert "account" in data
    assert data["account"]["cash"] == 10000.0
    assert data["account"]["portfolio_value"] == 15000.0
    assert data["account"]["buying_power"] == 10000.0
    assert data["account"]["currency"] == "USD"
    assert data["account"]["status"] == "ACTIVE"
    assert "positions" in data
    assert isinstance(data["positions"], list)
    assert data["positions"] == []


def test_get_account_failure(auth_client):
    """GET /api/trading/account → Alpaca 오류 시 503 반환."""
    with patch("app.api.trading.alpaca_client.get_account", side_effect=Exception("API error")):  # noqa: E501
        resp = auth_client.get("/api/trading/account")
    assert resp.status_code == 503


def test_place_order_buy_success(auth_client):
    """POST /api/trading/orders → buy 주문 성공."""
    _patch_order = patch("app.application.tools.alpaca_client.place_order", return_value=_MOCK_ORDER)  # noqa: E501
    _patch_sync = patch("app.application.tools.alpaca_client.sync_positions", return_value=[])  # noqa: E501
    with _patch_order, _patch_sync:
        resp = auth_client.post(
            "/api/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "qty": 1.0},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["order"]["ticker"] == "AAPL"
    assert "log_id" in data
    order = data["order"]
    assert order["alpaca_id"] == "test-order-id-123"
    assert order["side"] == "buy"
    assert order["qty"] == 1.0
    assert order["status"] == "filled"
    assert order["filled_avg_price"] == pytest.approx(150.0)


def test_place_order_failure(auth_client):
    """POST /api/trading/orders → Alpaca 오류 시 success=False."""
    with patch("app.application.tools.alpaca_client.place_order", side_effect=Exception("Order rejected")):  # noqa: E501
        resp = auth_client.post(
            "/api/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "qty": 1.0},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "error" in data
    assert "Order rejected" in data["error"]


def test_place_order_logged_on_failure(auth_client):
    """POST /api/trading/orders → 실패 시에도 trade log에 failed 상태로 기록."""
    with patch("app.application.tools.alpaca_client.place_order", side_effect=Exception("Connection error")):  # noqa: E501
        resp = auth_client.post(
            "/api/trading/orders",
            json={"ticker": "TSLA", "side": "buy", "qty": 2.0},
        )
    assert resp.json()["success"] is False

    # Failed order should appear in logs with status=failed
    log_resp = auth_client.get("/api/trading/logs?limit=100&offset=0")
    logs = log_resp.json()["logs"]
    failed_logs = [lg for lg in logs if lg["ticker"] == "TSLA" and lg["status"] == "failed"]
    assert len(failed_logs) >= 1
    assert failed_logs[0]["side"] == "buy"
    assert failed_logs[0]["qty"] == 2.0


def test_get_trade_logs(auth_client, db_trade_log):
    """GET /api/trading/logs → 거래 로그 목록 및 페이징 필드 반환."""
    resp = auth_client.get("/api/trading/logs")
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["logs"], list)
    assert data["total"] >= len(data["logs"])

    our_log = next(lg for lg in data["logs"] if lg["id"] == db_trade_log["id"])
    for field in ("ticker", "side", "qty", "order_type", "status"):
        assert field in our_log
    assert our_log["ticker"] == "TESTLOG"
    assert our_log["side"] == "buy"
    assert our_log["qty"] == pytest.approx(3.0)
    assert our_log["order_type"] == "market"
    assert our_log["status"] == "filled"


def test_get_trade_logs_limit(auth_client):
    """GET /api/trading/logs?limit=5 → limit 파라미터 수용."""
    resp = auth_client.get("/api/trading/logs?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) <= 5
    assert data["limit"] == 5


def test_get_trade_logs_offset(auth_client):
    """GET /api/trading/logs?offset=N → offset 파라미터가 응답에 반영된다."""
    resp = auth_client.get("/api/trading/logs?limit=10&offset=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 5
    assert data["limit"] == 10
    assert "total" in data


def test_get_trade_logs_offset_beyond_total(auth_client):
    """GET /api/trading/logs?offset=9999 → 빈 목록, total은 실제 총 건수."""
    resp_all = auth_client.get("/api/trading/logs?limit=1&offset=0")
    total = resp_all.json()["total"]

    resp = auth_client.get(f"/api/trading/logs?limit=10&offset={total + 1000}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["logs"] == []
    assert data["total"] == total


def test_place_order_with_strategy_id(auth_client):
    """POST /api/trading/orders → strategy_id 포함 주문."""
    _patch_order = patch("app.application.tools.alpaca_client.place_order", return_value=_MOCK_ORDER)  # noqa: E501
    _patch_sync = patch("app.application.tools.alpaca_client.sync_positions", return_value=[])  # noqa: E501
    with _patch_order, _patch_sync:
        resp = auth_client.post(
            "/api/trading/orders",
            json={
                "ticker": "AAPL",
                "side": "buy",
                "qty": 1.0,
                "strategy_id": None,
                "ai_reasoning": "Test order",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["order"]["ticker"] == "AAPL"
    assert "holdings_synced" in data
