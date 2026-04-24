"""Unit tests for repair_realized_trades_from_db and reconcile_fills."""

from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# repair_realized_trades_from_db
# ---------------------------------------------------------------------------


def _make_orphan(trade_log_id=1, ticker="AAPL", qty=10.0, filled_price=150.0, avg_cost=100.0):
    return {
        "id": trade_log_id,
        "ticker": ticker,
        "side": "sell",
        "status": "filled",
        "qty": qty,
        "filled_price": filled_price,
        "avg_cost_snapshot": avg_cost,
        "currency": "USD",
        "strategy_id": None,
    }


def test_repair_inserts_missing_realized_trade():
    orphan = _make_orphan()
    with (
        patch("app.application.tools.db.list_orphan_sell_logs", return_value=[orphan]),
        patch(
            "app.application.tools.db.upsert_realized_trade_by_trade_log_id",
            return_value=("inserted", 1),
        ) as mock_upsert,
    ):
        from app.application.tools import repair_realized_trades_from_db

        result = repair_realized_trades_from_db()

    assert result["repaired"] == 1
    assert result["skipped_no_cost"] == 0
    mock_upsert.assert_called_once()
    call_kwargs = mock_upsert.call_args.kwargs
    assert call_kwargs["trade_log_id"] == 1
    assert call_kwargs["sell_price"] == pytest.approx(150.0)
    assert call_kwargs["avg_cost"] == pytest.approx(100.0)
    assert call_kwargs["realized_pnl"] == pytest.approx((150.0 - 100.0) * 10.0)


def test_repair_skips_when_already_exists():
    orphan = _make_orphan()
    with (
        patch("app.application.tools.db.list_orphan_sell_logs", return_value=[orphan]),
        patch(
            "app.application.tools.db.upsert_realized_trade_by_trade_log_id",
            return_value=("unchanged", 1),
        ),
    ):
        from app.application.tools import repair_realized_trades_from_db

        result = repair_realized_trades_from_db()

    assert result["repaired"] == 0


def test_repair_skips_no_avg_cost():
    orphan = _make_orphan(avg_cost=None)
    orphan["avg_cost_snapshot"] = None
    with (
        patch("app.application.tools.db.list_orphan_sell_logs", return_value=[orphan]),
        patch("app.application.tools.db.upsert_realized_trade_by_trade_log_id") as mock_upsert,
    ):
        from app.application.tools import repair_realized_trades_from_db

        result = repair_realized_trades_from_db()

    assert result["skipped_no_cost"] == 1
    mock_upsert.assert_not_called()


def test_repair_empty_orphans():
    with patch("app.application.tools.db.list_orphan_sell_logs", return_value=[]):
        from app.application.tools import repair_realized_trades_from_db

        result = repair_realized_trades_from_db()
    assert result == {"repaired": 0, "skipped_no_cost": 0}


# ---------------------------------------------------------------------------
# sync_pending_orders
# ---------------------------------------------------------------------------


def test_sync_pending_orders_returns_structured_dict():
    pending = {
        "id": 10,
        "broker_order_id": "ORD001",
        "ticker": "005930",
        "side": "sell",
        "qty": 5.0,
        "filled_price": None,
        "avg_cost_snapshot": 70000.0,
        "currency": "KRW",
        "market": "KR",
        "strategy_id": None,
    }
    order_response = {"status": "filled", "filled_avg_price": 75000.0}

    with (
        patch("app.application.tools.db.get_pending_fill_logs", return_value=[pending]),
        patch("app.application.tools.kis_client.get_order", return_value=order_response),
        patch("app.application.tools.db.update_trade_log_status"),
        patch(
            "app.application.tools.db.upsert_realized_trade_by_trade_log_id",
            return_value=("inserted", 20),
        ),
        patch("app.application.tools._sync_from_broker", return_value=True),
    ):
        from app.application.tools import sync_pending_orders

        result = sync_pending_orders()

    assert result["updated"] == 1
    assert result["still_pending"] == 0
    assert result["errors"] == []


def test_sync_pending_orders_isolates_single_error():
    """한 건 실패해도 다음 건 계속 처리."""
    logs = [
        {
            "id": 1,
            "broker_order_id": "BAD",
            "ticker": "AAPL",
            "side": "sell",
            "qty": 1.0,
            "filled_price": None,
            "avg_cost_snapshot": 100.0,
            "currency": "USD",
            "market": "US",
            "strategy_id": None,
        },
        {
            "id": 2,
            "broker_order_id": "OK",
            "ticker": "TSLA",
            "side": "sell",
            "qty": 2.0,
            "filled_price": None,
            "avg_cost_snapshot": 200.0,
            "currency": "USD",
            "market": "US",
            "strategy_id": None,
        },
    ]

    def fake_get_order(broker_order_id, market="US", lookback_days=7):
        if broker_order_id == "BAD":
            raise RuntimeError("KIS timeout")
        return {"status": "filled", "filled_avg_price": 250.0}

    with (
        patch("app.application.tools.db.get_pending_fill_logs", return_value=logs),
        patch("app.application.tools.kis_client.get_order", side_effect=fake_get_order),
        patch("app.application.tools.db.update_trade_log_status"),
        patch(
            "app.application.tools.db.upsert_realized_trade_by_trade_log_id",
            return_value=("inserted", 5),
        ),
        patch("app.application.tools._sync_from_broker", return_value=True),
    ):
        from app.application.tools import sync_pending_orders

        result = sync_pending_orders()

    assert result["updated"] == 1
    assert len(result["errors"]) == 1
    assert result["errors"][0]["broker_order_id"] == "BAD"


# ---------------------------------------------------------------------------
# list_orphan_sell_logs (repository layer)
# ---------------------------------------------------------------------------


def test_list_orphan_sell_logs_integration(app_client):
    """DB에 realized_trade 없는 filled sell trade_log가 orphan으로 반환되는지 확인."""
    from app.infrastructure import repository as db

    # trade_log 삽입 (filled sell)
    log = db.add_trade_log(
        ticker="AAPL",
        side="sell",
        qty=5.0,
        order_type="market",
        status="filled",
        filled_price=150.0,
        avg_cost_snapshot=100.0,
        currency="USD",
        market="US",
    )
    log_id = log["id"]

    orphans = db.list_orphan_sell_logs()
    assert any(o["id"] == log_id for o in orphans)

    # realized_trade 삽입 후 orphan 목록에서 사라지는지 확인
    db.upsert_realized_trade_by_trade_log_id(
        trade_log_id=log_id,
        ticker="AAPL",
        qty=5.0,
        sell_price=150.0,
        avg_cost=100.0,
        realized_pnl=250.0,
        realized_pnl_pct=50.0,
        currency="USD",
    )
    orphans_after = db.list_orphan_sell_logs()
    assert not any(o["id"] == log_id for o in orphans_after)


def test_upsert_realized_trade_idempotent(app_client):
    """같은 trade_log_id로 두 번 upsert해도 중복 삽입 안 됨."""
    from app.infrastructure import repository as db

    log = db.add_trade_log(
        ticker="TSLA",
        side="sell",
        qty=2.0,
        order_type="market",
        status="filled",
        filled_price=300.0,
        avg_cost_snapshot=200.0,
        currency="USD",
        market="US",
    )
    log_id = log["id"]

    action1, rid1 = db.upsert_realized_trade_by_trade_log_id(
        trade_log_id=log_id,
        ticker="TSLA",
        qty=2.0,
        sell_price=300.0,
        avg_cost=200.0,
        realized_pnl=200.0,
        realized_pnl_pct=50.0,
        currency="USD",
    )
    action2, rid2 = db.upsert_realized_trade_by_trade_log_id(
        trade_log_id=log_id,
        ticker="TSLA",
        qty=2.0,
        sell_price=300.0,
        avg_cost=200.0,
        realized_pnl=200.0,
        realized_pnl_pct=50.0,
        currency="USD",
    )

    assert action1 == "inserted"
    assert action2 == "unchanged"
    assert rid1 == rid2
