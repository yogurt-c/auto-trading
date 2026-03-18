"""E2E tests: 전략 저장 → 조회 → 상태변경 → 삭제 전체 흐름.

DB: real Alembic SQLite (data/test.db)
External: Alpaca + yfinance only are mocked.
"""

from unittest.mock import patch

import pytest


def test_full_strategy_lifecycle(app_client):
    """전략 생성 → 조회 → active 상태변경 → 삭제 전체 흐름."""
    payload = {
        "name": "E2E Lifecycle Strategy",
        "strategy_type": "value",
        "ticker": "TSLA",
        "entry_price_drop_pct": -10.0,
        "take_profit_pct": 30.0,
        "stop_loss_pct": -15.0,
    }

    # 1. 전략 생성
    create_resp = app_client.post("/api/strategies", json=payload)
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["success"] is True
    strategy_id = create_data["strategy"]["id"]
    assert create_data["strategy"]["ticker"] == "TSLA"
    assert create_data["strategy"]["entry_price_drop_pct"] == pytest.approx(-10.0)
    assert create_data["strategy"]["take_profit_pct"] == pytest.approx(30.0)
    assert create_data["strategy"]["stop_loss_pct"] == pytest.approx(-15.0)

    try:
        # 2. 목록 조회 — 생성된 전략 포함 확인
        list_resp = app_client.get("/api/strategies")
        assert list_resp.status_code == 200
        ids = [s["id"] for s in list_resp.json()]
        assert strategy_id in ids

        # 3. 상태변경: paused → active
        patch_resp = app_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["strategy"]["status"] == "active"

        # Active 필터에서도 포함 확인
        active_resp = app_client.get("/api/strategies?status=active")
        assert active_resp.status_code == 200
        active_ids = [s["id"] for s in active_resp.json()]
        assert strategy_id in active_ids

        # Paused 필터에서는 제외 확인
        paused_resp = app_client.get("/api/strategies?status=paused")
        paused_ids = [s["id"] for s in paused_resp.json()]
        assert strategy_id not in paused_ids

        # 4. 삭제
        del_resp = app_client.delete(f"/api/strategies/{strategy_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True
        strategy_id = None  # Prevent double-delete in finally

        # 삭제 후 목록에서 사라진 것 확인
        list_resp2 = app_client.get("/api/strategies")
        remaining_ids = [s["id"] for s in list_resp2.json()]
        assert strategy_id not in remaining_ids

    finally:
        if strategy_id is not None:
            app_client.delete(f"/api/strategies/{strategy_id}")


def test_portfolio_e2e_with_mock_prices(app_client):
    """GET /api/portfolio → mock prices로 P&L 포함 전체 응답 검증."""
    holdings = [
        {"ticker": "AAPL", "shares": 5.0, "avg_price": 150.0},
        {"ticker": "MSFT", "shares": 2.0, "avg_price": 300.0},
    ]
    prices = {"AAPL": 180.0, "MSFT": 350.0}

    with patch("backend.api.portfolio.db.get_all_holdings", return_value=holdings), \
         patch("api.portfolio.get_current_prices", return_value=prices):
        resp = app_client.get("/api/portfolio")

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["failed_tickers"] == []

    tickers = {h["ticker"] for h in data["holdings"]}
    assert tickers == {"AAPL", "MSFT"}

    # AAPL: (180-150)*5 = 150 profit
    # MSFT: (350-300)*2 = 100 profit → total = 250
    summary = data["summary"]
    assert summary["total_pnl"] == pytest.approx(250.0)
    assert summary["total_market_value"] == pytest.approx(5 * 180.0 + 2 * 350.0)
    assert summary["total_cost_basis"] == pytest.approx(1350.0)  # 5*150 + 2*300

    aapl_h = next(h for h in data["holdings"] if h["ticker"] == "AAPL")
    msft_h = next(h for h in data["holdings"] if h["ticker"] == "MSFT")
    assert aapl_h["pnl_pct"] == pytest.approx(20.0)
    assert msft_h["pnl_pct"] == pytest.approx(50 / 3, abs=0.1)  # (350-300)/300*100 ≈ 16.67


def test_strategy_create_and_dca_check(app_client):
    """전략 생성 → DCA 실행 여부 확인 전체 흐름."""
    s_resp = app_client.post(
        "/api/strategies",
        json={
            "name": "E2E DCA Flow",
            "strategy_type": "dca",
            "ticker": "SPY",
            "dca_amount_usd": 200.0,
            "dca_frequency_days": 14,
        },
    )
    assert s_resp.status_code == 200
    strategy_id = s_resp.json()["strategy"]["id"]

    try:
        # 1. DCA 실행 여부 확인 (한 번도 안 했으니 is_due=True)
        dca_resp = app_client.get(f"/api/strategies/{strategy_id}/dca-due")
        assert dca_resp.status_code == 200
        dca_data = dca_resp.json()
        assert dca_data["is_due"] is True
        assert dca_data["dca_frequency_days"] == 14
        assert "Never" in dca_data["reason"]

        # 2. Activate + complete lifecycle
        app_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "active"},
        )
        app_client.patch(
            f"/api/strategies/{strategy_id}/status",
            json={"status": "completed"},
        )

        completed_resp = app_client.get("/api/strategies?status=completed")
        completed_ids = [s["id"] for s in completed_resp.json()]
        assert strategy_id in completed_ids

    finally:
        app_client.delete(f"/api/strategies/{strategy_id}")
