"""Integration tests for Strategies API endpoints.

DB: real Alembic SQLite (data/test.db).
Each test cleans up its own data to avoid interference.
"""

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_strategy(client, **kwargs):
    """Helper: POST /api/strategies and return the strategy dict."""
    payload = {"name": "Test Strategy", "strategy_type": "value"}
    payload.update(kwargs)
    resp = client.post("/api/strategies", json=payload)
    assert resp.status_code == 200
    return resp.json()["strategy"]


def _delete_strategy(client, strategy_id):
    client.delete(f"/api/strategies/{strategy_id}")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_strategies_returns_list(auth_client):
    """GET /api/strategies → strategies 목록을 list로 반환."""
    resp = auth_client.get("/api/strategies")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_strategy(auth_client):
    """POST /api/strategies → success=True, strategy dict 반환."""
    payload = {
        "name": "AAPL Value Strategy",
        "strategy_type": "value",
        "ticker": "AAPL",
        "entry_price_drop_pct": -5.0,
        "take_profit_pct": 20.0,
        "stop_loss_pct": -10.0,
    }
    resp = auth_client.post("/api/strategies", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    s = data["strategy"]
    assert s["name"] == "AAPL Value Strategy"
    assert s["ticker"] == "AAPL"
    assert s["entry_price_drop_pct"] == -5.0
    assert s["strategy_type"] == "value"
    assert s["take_profit_pct"] == pytest.approx(20.0)
    assert s["stop_loss_pct"] == pytest.approx(-10.0)
    assert "status" in s
    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    strategy_id = s["id"]
    _delete_strategy(auth_client, strategy_id)


def test_create_strategy_appears_in_list(auth_client):
    """POST → 생성된 전략이 GET 목록에 포함된다."""
    s = _create_strategy(auth_client, name="List Check Strategy", strategy_type="custom")
    strategy_id = s["id"]
    try:
        resp = auth_client.get("/api/strategies")
        ids = [x["id"] for x in resp.json()]
        assert strategy_id in ids
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_update_strategy_status_active(auth_client):
    """PATCH /api/strategies/{id}/status → active 변경."""
    s = _create_strategy(auth_client, name="Status Update Test")
    strategy_id = s["id"]
    try:
        resp = auth_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["strategy"]["status"] == "active"
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_update_strategy_status_paused(auth_client):
    """PATCH /api/strategies/{id}/status → paused 변경."""
    s = _create_strategy(auth_client, name="Pause Test")
    strategy_id = s["id"]
    try:
        resp = auth_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "paused"},
        )
        assert resp.status_code == 200
        assert resp.json()["strategy"]["status"] == "paused"
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_update_strategy_status_not_found(auth_client):
    """PATCH /api/strategies/999999/status → 404."""
    resp = auth_client.patch("/api/strategies/999999/status", json={"status": "active"})
    assert resp.status_code == 404


def test_delete_strategy_success(auth_client):
    """DELETE /api/strategies/{id} → success=True."""
    s = _create_strategy(auth_client, name="Delete Me")
    strategy_id = s["id"]
    resp = auth_client.delete(f"/api/strategies/{strategy_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_delete_strategy_not_found(auth_client):
    """DELETE /api/strategies/999999 → 404."""
    resp = auth_client.delete("/api/strategies/999999")
    assert resp.status_code == 404


def test_delete_strategy_removed_from_list(auth_client):
    """DELETE 후 GET 목록에서 사라진다."""
    s = _create_strategy(auth_client, name="Remove From List")
    strategy_id = s["id"]
    auth_client.delete(f"/api/strategies/{strategy_id}")
    resp = auth_client.get("/api/strategies")
    ids = [x["id"] for x in resp.json()]
    assert strategy_id not in ids


def test_get_strategies_status_filter(auth_client):
    """GET /api/strategies?status=active → active 전략만 반환."""
    s = _create_strategy(auth_client, name="Filter Active Test")
    strategy_id = s["id"]
    try:
        # Activate the strategy
        auth_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
        )
        resp = auth_client.get("/api/strategies?status=active")
        assert resp.status_code == 200
        statuses = [x["status"] for x in resp.json()]
        assert all(st == "active" for st in statuses)
        assert strategy_id in [x["id"] for x in resp.json()]
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_evaluate_strategy_no_ticker(auth_client):
    """GET /api/strategies/{id}/evaluate → ticker 없으면 error 반환."""
    s = _create_strategy(auth_client, name="No Ticker Eval", ticker=None)
    strategy_id = s["id"]
    try:
        resp = auth_client.get(f"/api/strategies/{strategy_id}/evaluate")
        assert resp.status_code == 200
        assert "error" in resp.json()
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_evaluate_strategy_not_found(auth_client):
    """GET /api/strategies/999999/evaluate → error 반환."""
    resp = auth_client.get("/api/strategies/999999/evaluate")
    assert resp.status_code == 200
    assert "error" in resp.json()


def test_dca_due_no_frequency(auth_client):
    """GET /api/strategies/{id}/dca-due → DCA 아닌 전략은 is_due=False."""
    s = _create_strategy(auth_client, name="No DCA", strategy_type="value")
    strategy_id = s["id"]
    try:
        resp = auth_client.get(f"/api/strategies/{strategy_id}/dca-due")
        assert resp.status_code == 200
        dca_data = resp.json()
        assert dca_data["is_due"] is False
        assert isinstance(dca_data["reason"], str)
        assert len(dca_data["reason"]) > 0
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_dca_due_never_triggered(auth_client):
    """GET /api/strategies/{id}/dca-due → 한 번도 실행 안 됐으면 is_due=True."""
    s = _create_strategy(
        auth_client,
        name="New DCA",
        strategy_type="dca",
        dca_amount_usd=100.0,
        dca_frequency_days=7,
    )
    strategy_id = s["id"]
    try:
        resp = auth_client.get(f"/api/strategies/{strategy_id}/dca-due")
        assert resp.status_code == 200
        dca_data = resp.json()
        assert dca_data["is_due"] is True
        assert "Never" in dca_data["reason"]
        assert dca_data.get("days_since_last") is None
        assert dca_data["dca_frequency_days"] == 7
    finally:
        _delete_strategy(auth_client, strategy_id)


def test_dca_due_not_found(auth_client):
    """GET /api/strategies/999999/dca-due → error 반환."""
    resp = auth_client.get("/api/strategies/999999/dca-due")
    assert resp.status_code == 200
    assert "error" in resp.json()
