"""Integration tests for GET /api/portfolio/performance."""

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_realized_trade(
    id: int = 1,
    ticker: str = "AAPL",
    qty: float = 10.0,
    sell_price: float = 150.0,
    avg_cost: float = 100.0,
    strategy_id: int | None = None,
    executed_at: str = "2026-03-15T14:30:00",
    currency: str = "USD",
) -> dict:
    pnl = (sell_price - avg_cost) * qty
    pnl_pct = round((pnl / (avg_cost * qty) * 100) if avg_cost else 0.0, 2)
    return {
        "id": id,
        "trade_log_id": id,
        "ticker": ticker,
        "qty": qty,
        "sell_price": sell_price,
        "avg_cost": avg_cost,
        "realized_pnl": pnl,
        "realized_pnl_pct": pnl_pct,
        "currency": currency,
        "strategy_id": strategy_id,
        "executed_at": executed_at,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_performance_empty_data(auth_client):
    """realized_trades 없을 때 → by_currency 빈 리스트 응답."""
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=[]),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_currency"] == []
    assert data["trades"] == []
    assert data["by_period"] == []
    assert data["by_strategy"] == []


def test_performance_with_data(auth_client):
    """정상 데이터 → by_currency에 USD 집계 반환."""
    rt = _make_realized_trade(sell_price=150.0, avg_cost=100.0, qty=10.0, currency="USD")
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=[rt]),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_currency"]) == 1
    usd = data["by_currency"][0]
    assert usd["currency"] == "USD"
    assert usd["total_realized_pnl"] == pytest.approx(500.0)
    assert usd["total_trade_count"] == 1
    assert usd["win_count"] == 1
    assert usd["win_rate"] == pytest.approx(100.0)
    assert len(data["trades"]) == 1
    assert data["trades"][0]["ticker"] == "AAPL"


def test_performance_response_structure(auth_client):
    """응답에 필수 필드가 모두 포함되어 있는지 확인."""
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=[]),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    assert resp.status_code == 200
    data = resp.json()
    required_keys = {"period_start", "period_end", "by_currency", "trades", "by_period", "by_strategy"}
    assert required_keys <= data.keys()


def test_performance_default_dates(auth_client):
    """start_date / end_date 생략 시 기본값으로 동작 (400 없음)."""
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=[]),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get("/api/portfolio/performance")
    assert resp.status_code == 200


def test_performance_invalid_group_by(auth_client):
    """잘못된 group_by 값 → 422 Unprocessable Entity."""
    resp = auth_client.get(
        "/api/portfolio/performance",
        params={"start_date": "2026-03-01", "end_date": "2026-03-31", "group_by": "week"},
    )
    assert resp.status_code == 422


def test_performance_start_after_end(auth_client):
    """start_date > end_date → 400 반환."""
    resp = auth_client.get(
        "/api/portfolio/performance",
        params={"start_date": "2026-03-31", "end_date": "2026-03-01"},
    )
    assert resp.status_code == 400


def test_performance_group_by_month(auth_client):
    """group_by=month → by_period 월별 집계."""
    trades = [
        _make_realized_trade(
            id=1, sell_price=120.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-05T10:00:00"
        ),
        _make_realized_trade(
            id=2, sell_price=110.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-20T10:00:00"
        ),
    ]
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=trades),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31", "group_by": "month"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_period"]) == 1
    assert data["by_period"][0]["period"] == "2026-03"
    assert data["by_period"][0]["currency"] == "USD"
    assert data["by_period"][0]["trade_count"] == 2


def test_performance_with_strategy_names(auth_client):
    """전략 이름이 trades 결과에 포함되는지 확인."""
    rt = _make_realized_trade(strategy_id=1)
    strategies = [{"id": 1, "name": "My Strategy"}]
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=[rt]),
        patch("app.application.tools.db.get_strategies", return_value=strategies),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trades"][0]["strategy_name"] == "My Strategy"
    assert data["by_strategy"][0]["strategy_name"] == "My Strategy"


def test_performance_by_strategy_splits_currency(auth_client):
    """같은 전략이 KRW/USD 거래 → by_strategy에 통화별 2개 row."""
    trades = [
        _make_realized_trade(id=1, ticker="AAPL", currency="USD", sell_price=150.0, avg_cost=100.0, qty=10.0, strategy_id=1),
        _make_realized_trade(id=2, ticker="005930", currency="KRW", sell_price=80000.0, avg_cost=60000.0, qty=5.0, strategy_id=1),
    ]
    strategies = [{"id": 1, "name": "Mixed"}]
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=trades),
        patch("app.application.tools.db.get_strategies", return_value=strategies),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_strategy"]) == 2
    rows = {s["currency"]: s for s in data["by_strategy"]}
    assert "USD" in rows and "KRW" in rows
    assert rows["USD"]["realized_pnl"] == pytest.approx(500.0)
    assert rows["KRW"]["realized_pnl"] == pytest.approx(100_000.0)


def test_performance_by_period_splits_currency(auth_client):
    """동일 날짜 KRW + USD 거래 → by_period에 통화별 2개 row."""
    trades = [
        _make_realized_trade(
            id=1,
            ticker="AAPL",
            currency="USD",
            sell_price=150.0,
            avg_cost=100.0,
            qty=10.0,
            executed_at="2026-03-10T10:00:00",
        ),
        _make_realized_trade(
            id=2,
            ticker="005930",
            currency="KRW",
            sell_price=80000.0,
            avg_cost=60000.0,
            qty=5.0,
            executed_at="2026-03-10T11:00:00",
        ),
    ]
    with (
        patch("app.application.tools.db.get_realized_trades", return_value=trades),
        patch("app.application.tools.db.get_strategies", return_value=[]),
    ):
        resp = auth_client.get(
            "/api/portfolio/performance",
            params={"start_date": "2026-03-01", "end_date": "2026-03-31", "group_by": "day"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["by_period"]) == 2
    buckets = {(p["period"], p["currency"]): p for p in data["by_period"]}
    assert ("2026-03-10", "USD") in buckets
    assert ("2026-03-10", "KRW") in buckets
    assert buckets[("2026-03-10", "USD")]["realized_pnl"] == pytest.approx(500.0)
    assert buckets[("2026-03-10", "KRW")]["realized_pnl"] == pytest.approx(100_000.0)
