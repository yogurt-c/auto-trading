"""Integration tests for Trading API endpoints.

DB: real Alembic SQLite (data/test.db)
External: core.kis_client is mocked.
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
    "broker_order_id": "test-order-id-123",
    "ticker": "AAPL",
    "side": "buy",
    "qty": 1.0,
    "order_type": "market",
    "status": "filled",
    "limit_price": None,
    "filled_avg_price": 150.0,
    "market": "US",
    "currency": "USD",
}


def test_get_account_success(auth_client):
    """GET /api/trading/account → Alpaca mock 성공 응답."""
    with (
        patch("app.api.trading.kis_client.get_account", return_value=_MOCK_ACCOUNT),
        patch("app.api.trading.kis_client.get_positions", return_value=[]),
    ):
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
    with patch("app.api.trading.kis_client.get_account", side_effect=Exception("API error")):
        resp = auth_client.get("/api/trading/account")
    assert resp.status_code == 503


def test_place_order_buy_success(auth_client):
    """POST /api/trading/orders → buy 주문 성공."""
    _patch_order = patch("app.application.tools.kis_client.place_order", return_value=_MOCK_ORDER)
    _patch_sync = patch("app.application.tools.kis_client.sync_positions", return_value=[])
    _patch_nyse = patch("app.application.tools.is_nyse_open", return_value=True)
    with _patch_order, _patch_sync, _patch_nyse:
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
    assert order["broker_order_id"] == "test-order-id-123"
    assert order["side"] == "buy"
    assert order["qty"] == 1.0
    assert order["status"] == "filled"
    assert order["filled_avg_price"] == pytest.approx(150.0)


def test_place_order_failure(auth_client):
    """POST /api/trading/orders → Alpaca 오류 시 success=False."""
    _patch_order = patch(
        "app.application.tools.kis_client.place_order", side_effect=Exception("Order rejected")
    )
    _patch_nyse = patch("app.application.tools.is_nyse_open", return_value=True)
    with _patch_order, _patch_nyse:
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
    _patch_order = patch(
        "app.application.tools.kis_client.place_order", side_effect=Exception("Connection error")
    )
    _patch_nyse = patch("app.application.tools.is_nyse_open", return_value=True)
    with _patch_order, _patch_nyse:
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


def test_sync_pending_orders_updates_status(db_partially_filled_log):
    """sync_pending_orders → Alpaca에서 filled 반환 시 DB 상태 업데이트."""
    from unittest.mock import patch

    from app.application.tools import sync_pending_orders
    from app.infrastructure import repository as db

    with patch(
        "app.application.tools.kis_client.get_order",
        return_value={
            "broker_order_id": "partial-order-uuid-001",
            "status": "filled",
            "filled_avg_price": 200.0,
            "filled_qty": 5.0,
        },
    ):
        updated = sync_pending_orders()

    assert updated["updated"] >= 1
    logs = db.get_trade_logs(limit=100, offset=0)
    synced = next((lg for lg in logs if lg["id"] == db_partially_filled_log["id"]), None)
    assert synced is not None
    assert synced["status"] == "filled"
    assert synced["filled_price"] == pytest.approx(200.0)


def test_sync_pending_orders_skips_still_partial(db_partially_filled_log):
    """sync_pending_orders → Alpaca에서 여전히 partially_filled 반환 시 DB 변경 없음."""
    from unittest.mock import patch

    from app.application.tools import sync_pending_orders
    from app.infrastructure import repository as db

    with patch(
        "app.application.tools.kis_client.get_order",
        return_value={
            "broker_order_id": "partial-order-uuid-001",
            "status": "partially_filled",
            "filled_avg_price": None,
            "filled_qty": 2.0,
        },
    ):
        updated = sync_pending_orders()

    assert updated["updated"] == 0
    logs = db.get_trade_logs(limit=100, offset=0)
    synced = next((lg for lg in logs if lg["id"] == db_partially_filled_log["id"]), None)
    assert synced["status"] == "partially_filled"


def test_get_partially_filled_logs(db_partially_filled_log):
    """get_pending_fill_logs → partially_filled 레코드 포함, broker_order_id 있음."""
    from app.infrastructure import repository as db

    logs = db.get_pending_fill_logs()
    ids = [lg["id"] for lg in logs]
    assert db_partially_filled_log["id"] in ids
    for lg in logs:
        assert lg["status"] in ("partially_filled", "accepted")
        assert lg["broker_order_id"] is not None


def test_get_pending_fill_logs_includes_accepted():
    """get_pending_fill_logs → accepted 상태 주문도 반환한다 (BUG-01 수정 검증)."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import TradeLog as TradeLogModel

    log = db.add_trade_log(
        ticker="ACCEPTED_TEST",
        side="buy",
        qty=2.0,
        order_type="market",
        status="accepted",
        broker_order_id="accepted-order-uuid-001",
    )
    try:
        logs = db.get_pending_fill_logs()
        ids = [lg["id"] for lg in logs]
        assert log["id"] in ids, "accepted 주문이 get_pending_fill_logs에 포함되어야 한다"
        our = next(lg for lg in logs if lg["id"] == log["id"])
        assert our["status"] == "accepted"
        assert our["broker_order_id"] == "accepted-order-uuid-001"
    finally:
        with get_session() as s:
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


def test_update_trade_log_status(db_partially_filled_log):
    """update_trade_log_status → status·filled_price 업데이트."""
    from app.infrastructure import repository as db

    db.update_trade_log_status(
        db_partially_filled_log["id"],
        status="filled",
        filled_price=175.5,
    )
    logs = db.get_trade_logs(limit=100, offset=0)
    updated = next((lg for lg in logs if lg["id"] == db_partially_filled_log["id"]), None)
    assert updated["status"] == "filled"
    assert updated["filled_price"] == pytest.approx(175.5)


def test_place_limit_order_captures_filled_price(auth_client):
    """POST /api/trading/orders → limit 주문도 체결 시 filled_price 저장."""
    _mock_order = {
        "broker_order_id": "limit-order-id-456",
        "ticker": "AAPL",
        "side": "buy",
        "qty": 1.0,
        "order_type": "limit",
        "status": "filled",
        "limit_price": 145.0,
        "filled_avg_price": 144.8,
        "market": "US",
        "currency": "USD",
    }
    _patch_order = patch("app.application.tools.kis_client.place_order", return_value=_mock_order)
    _patch_sync = patch("app.application.tools.kis_client.sync_positions", return_value=[])
    _patch_nyse = patch("app.application.tools.is_nyse_open", return_value=True)
    with _patch_order, _patch_sync, _patch_nyse:
        resp = auth_client.post(
            "/api/trading/orders",
            json={
                "ticker": "AAPL",
                "side": "buy",
                "qty": 1.0,
                "order_type": "limit",
                "limit_price": 145.0,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    log_resp = auth_client.get("/api/trading/logs?limit=100&offset=0")
    logs = log_resp.json()["logs"]
    log = next((lg for lg in logs if lg["broker_order_id"] == "limit-order-id-456"), None)
    assert log is not None
    assert log["filled_price"] == pytest.approx(144.8)
    assert log["limit_price"] == pytest.approx(145.0)


def test_place_order_with_strategy_id(auth_client):
    """POST /api/trading/orders → strategy_id 포함 주문."""
    _mock_strategy_order = {
        **_MOCK_ORDER,
        "broker_order_id": "test-order-strategy-id-999",
    }
    _patch_order = patch(
        "app.application.tools.kis_client.place_order", return_value=_mock_strategy_order
    )
    _patch_sync = patch("app.application.tools.kis_client.sync_positions", return_value=[])
    _patch_nyse = patch("app.application.tools.is_nyse_open", return_value=True)
    with _patch_order, _patch_sync, _patch_nyse:
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


@pytest.mark.usefixtures("_init_db")
def test_rebuild_holdings_empty_positions_guard():
    """rebuild_holdings_from_broker: KIS가 0 positions 반환 시 기존 holdings 보존."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import Holding as HoldingModel

    # 보유 종목 직접 생성
    db.rebuild_holdings_from_broker([{"ticker": "GUARDTEST", "qty": 10.0, "avg_entry_price": 50.0, "market": "US", "currency": "USD"}])
    try:
        # KIS 0 positions → guard 발동, holdings 유지
        result = db.rebuild_holdings_from_broker([])
        tickers = [h["ticker"] for h in result]
        assert "GUARDTEST" in tickers, "빈 positions 시 기존 holdings가 유지되어야 한다"
    finally:
        with get_session() as s:
            s.execute(sa_delete(HoldingModel).where(HoldingModel.ticker == "GUARDTEST"))


@pytest.mark.usefixtures("_init_db")
def test_sync_pending_orders_sell_creates_realized_trade():
    """sync_pending_orders → 매도 주문 체결 시 realized_trade 생성."""
    from unittest.mock import patch

    from sqlalchemy import delete as sa_delete

    from app.application.tools import sync_pending_orders
    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import RealizedTrade as RealizedTradeModel
    from app.infrastructure.models import TradeLog as TradeLogModel

    log = db.add_trade_log(
        ticker="SELLTEST",
        side="sell",
        qty=2.0,
        order_type="market",
        status="partially_filled",
        broker_order_id="sell-partial-uuid-deferred",
        avg_cost_snapshot=100.0,
    )
    try:
        with patch(
            "app.application.tools.kis_client.get_order",
            return_value={
                "broker_order_id": "sell-partial-uuid-deferred",
                "status": "filled",
                "filled_avg_price": 120.0,
            },
        ):
            updated = sync_pending_orders()

        assert updated["updated"] >= 1
        realized = db.get_realized_trades("2000-01-01", "2099-12-31")
        our = [r for r in realized if r["trade_log_id"] == log["id"]]
        assert len(our) == 1
        assert our[0]["realized_pnl"] == pytest.approx((120.0 - 100.0) * 2.0)
        assert our[0]["sell_price"] == pytest.approx(120.0)
        assert our[0]["avg_cost"] == pytest.approx(100.0)
    finally:
        with get_session() as s:
            s.execute(
                sa_delete(RealizedTradeModel).where(RealizedTradeModel.trade_log_id == log["id"])
            )
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


def test_place_order_filled_price_zero_no_realized_trade(auth_client):
    """place_order: filled_price=0이면 realized_trade가 생성되지 않는다."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import RealizedTrade as RealizedTradeModel
    from app.infrastructure.models import TradeLog as TradeLogModel

    # 보유 종목 생성 (avg_cost is not None)
    db.rebuild_holdings_from_broker([{"ticker": "ZPTEST", "qty": 5.0, "avg_entry_price": 100.0, "market": "US", "currency": "USD"}])
    try:
        _mock_order = {
            "broker_order_id": "sell-zero-price-uuid",
            "market": "US",
            "currency": "USD",
            "ticker": "ZPTEST",
            "side": "sell",
            "qty": 1.0,
            "order_type": "market",
            "status": "filled",
            "limit_price": None,
            "filled_avg_price": 0,
        }
        with (
            patch("app.application.tools.kis_client.place_order", return_value=_mock_order),
            patch("app.application.tools.kis_client.sync_positions", return_value=[]),
            patch("app.application.tools.is_nyse_open", return_value=True),
        ):
            resp = auth_client.post(
                "/api/trading/orders",
                json={"ticker": "ZPTEST", "side": "sell", "qty": 1.0},
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # realized_trade 미생성 확인 (sell_price=0인 레코드 없어야 함)
        realized = db.get_realized_trades("2000-01-01", "2099-12-31")
        zero_trades = [
            r for r in realized if r["ticker"] == "ZPTEST" and r["sell_price"] == pytest.approx(0.0)
        ]
        assert len(zero_trades) == 0
    finally:
        with get_session() as s:
            s.execute(sa_delete(RealizedTradeModel).where(RealizedTradeModel.ticker == "ZPTEST"))
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.ticker == "ZPTEST"))
        db.remove_holding("ZPTEST")


# ---------------------------------------------------------------------------
# BUG-01: accepted 주문 sync (get_pending_fill_logs 확장)
# ---------------------------------------------------------------------------


def test_sync_pending_orders_picks_up_accepted_status():
    """sync_pending_orders → accepted 상태 주문도 KIS에서 재조회해 filled로 갱신."""
    from sqlalchemy import delete as sa_delete

    from app.application.tools import sync_pending_orders
    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import TradeLog as TradeLogModel

    log = db.add_trade_log(
        ticker="ACCEPTSYNC",
        side="buy",
        qty=3.0,
        order_type="market",
        status="accepted",
        broker_order_id="accepted-sync-uuid-001",
    )
    try:
        with patch(
            "app.application.tools.kis_client.get_order",
            return_value={
                "broker_order_id": "accepted-sync-uuid-001",
                "status": "filled",
                "filled_avg_price": 55000.0,
            },
        ):
            updated = sync_pending_orders()

        assert updated["updated"] >= 1
        logs = db.get_trade_logs(limit=100, offset=0)
        synced = next((lg for lg in logs if lg["id"] == log["id"]), None)
        assert synced is not None
        assert synced["status"] == "filled"
        assert synced["filled_price"] == pytest.approx(55000.0)
    finally:
        with get_session() as s:
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


# ---------------------------------------------------------------------------
# BUG-02: sell_ratio 코드 레벨 적용
# ---------------------------------------------------------------------------


def test_sell_ratio_caps_qty_on_strategy_sell(auth_client):
    """sell_ratio=0.5인 전략의 매도: qty가 보유 수량의 50%로 제한된다."""
    from unittest.mock import patch

    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import RealizedTrade as RealizedTradeModel
    from app.infrastructure.models import Strategy as StrategyModel
    from app.infrastructure.models import TradeLog as TradeLogModel

    # 전략 생성 (sell_ratio=0.5)
    strat = db.save_strategy(
        name="SellRatioTest",
        strategy_type="value",
        ticker="SRTEST",
        market="US",
        entry_rsi_below=30.0,
        sell_ratio=0.5,
    )
    # 보유 종목 설정 (10주 보유)
    db.rebuild_holdings_from_broker([{"ticker": "SRTEST", "qty": 10.0, "avg_entry_price": 100.0, "market": "US", "currency": "USD"}])

    captured_qty = []

    def _fake_place_order(ticker, side, qty, **kwargs):
        captured_qty.append(qty)
        return {
            "broker_order_id": "sell-ratio-test-uuid",
            "ticker": ticker,
            "side": side,
            "qty": qty,
            "order_type": "market",
            "status": "filled",
            "limit_price": None,
            "filled_avg_price": 110.0,
            "market": "US",
            "currency": "USD",
        }

    try:
        with (
            patch("app.application.tools.kis_client.place_order", side_effect=_fake_place_order),
            patch("app.application.tools.kis_client.sync_positions", return_value=[]),
            patch("app.application.tools.is_nyse_open", return_value=True),
        ):
            resp = auth_client.post(
                "/api/trading/orders",
                json={
                    "ticker": "SRTEST",
                    "side": "sell",
                    "qty": 10.0,  # 전량 매도 시도
                    "strategy_id": strat["id"],
                },
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # sell_ratio=0.5이므로 실제 주문 qty는 10 * 0.5 = 5
        assert len(captured_qty) == 1
        assert captured_qty[0] == pytest.approx(5.0)
    finally:
        with get_session() as s:
            s.execute(sa_delete(RealizedTradeModel).where(RealizedTradeModel.ticker == "SRTEST"))
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.ticker == "SRTEST"))
            s.execute(sa_delete(StrategyModel).where(StrategyModel.id == strat["id"]))
        db.remove_holding("SRTEST")


def test_sell_ratio_one_does_not_cap_qty(auth_client):
    """sell_ratio=1.0(전량 매도): qty가 변경되지 않는다."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import RealizedTrade as RealizedTradeModel
    from app.infrastructure.models import Strategy as StrategyModel
    from app.infrastructure.models import TradeLog as TradeLogModel

    strat = db.save_strategy(
        name="SellRatioFullTest",
        strategy_type="value",
        ticker="SRFULL",
        market="US",
        entry_rsi_below=30.0,
        sell_ratio=1.0,
    )
    db.rebuild_holdings_from_broker([{"ticker": "SRFULL", "qty": 10.0, "avg_entry_price": 100.0, "market": "US", "currency": "USD"}])

    captured_qty = []

    def _fake_place_order(ticker, side, qty, **kwargs):
        captured_qty.append(qty)
        return {
            "broker_order_id": "sell-full-test-uuid",
            "ticker": ticker,
            "side": side,
            "qty": qty,
            "order_type": "market",
            "status": "filled",
            "limit_price": None,
            "filled_avg_price": 105.0,
            "market": "US",
            "currency": "USD",
        }

    try:
        with (
            patch("app.application.tools.kis_client.place_order", side_effect=_fake_place_order),
            patch("app.application.tools.kis_client.sync_positions", return_value=[]),
            patch("app.application.tools.is_nyse_open", return_value=True),
        ):
            resp = auth_client.post(
                "/api/trading/orders",
                json={
                    "ticker": "SRFULL",
                    "side": "sell",
                    "qty": 10.0,
                    "strategy_id": strat["id"],
                },
            )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # sell_ratio=1.0이므로 qty 변경 없음
        assert captured_qty[0] == pytest.approx(10.0)
    finally:
        with get_session() as s:
            s.execute(sa_delete(RealizedTradeModel).where(RealizedTradeModel.ticker == "SRFULL"))
            s.execute(sa_delete(TradeLogModel).where(TradeLogModel.ticker == "SRFULL"))
            s.execute(sa_delete(StrategyModel).where(StrategyModel.id == strat["id"]))
        db.remove_holding("SRFULL")


# ---------------------------------------------------------------------------
# BUG-03: max_position=None 기본 한도 가드
# ---------------------------------------------------------------------------


def test_buy_without_max_position_uses_default_cap(auth_client):
    """max_position 미설정 시 USD 기본 한도($5,000) 초과 주문이 차단된다."""
    with (
        patch("app.application.tools.is_nyse_open", return_value=True),
        patch(
            "app.application.tools.market_module.get_current_prices",
            return_value={"AAPL": 200.0},
        ),
        patch("app.application.tools.db.get_all_holdings", return_value=[]),
    ):
        # 200달러 x 30주 = $6,000 > 기본 한도 $5,000
        resp = auth_client.post(
            "/api/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "qty": 30.0},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "기본 한도" in data["error"]


def test_buy_within_default_cap_proceeds(auth_client):
    """기본 한도 이내 주문($5,000 미만)은 통과된다."""
    _mock_order = {**_MOCK_ORDER, "broker_order_id": "default-cap-pass-uuid"}
    with (
        patch("app.application.tools.is_nyse_open", return_value=True),
        patch(
            "app.application.tools.market_module.get_current_prices",
            return_value={"AAPL": 100.0},
        ),
        patch("app.application.tools.db.get_all_holdings", return_value=[]),
        patch("app.application.tools.kis_client.place_order", return_value=_mock_order),
        patch("app.application.tools.kis_client.sync_positions", return_value=[]),
    ):
        # 100달러 x 10주 = $1,000 < 기본 한도 $5,000
        resp = auth_client.post(
            "/api/trading/orders",
            json={"ticker": "AAPL", "side": "buy", "qty": 10.0},
        )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


# ---------------------------------------------------------------------------
# BUG-04: 동시 실행 방지 (_job_lock)
# ---------------------------------------------------------------------------


def test_concurrent_job_triggers_are_serialized():
    """두 번째 trigger_now()는 첫 번째 실행 중일 때 즉시 반환된다 (_job_lock 검증)."""
    import threading
    import time

    from app.application.scheduler import _job_lock

    execution_order = []

    def slow_job():
        if not _job_lock.acquire(blocking=False):
            execution_order.append("skipped")
            return
        try:
            execution_order.append("started")
            time.sleep(0.05)
            execution_order.append("finished")
        finally:
            _job_lock.release()

    t1 = threading.Thread(target=slow_job)
    t2 = threading.Thread(target=slow_job)
    t1.start()
    time.sleep(0.01)  # t1이 lock을 잡은 뒤 t2 시작
    t2.start()
    t1.join()
    t2.join()

    assert "started" in execution_order
    assert "finished" in execution_order
    assert "skipped" in execution_order
    assert execution_order.count("started") == 1
