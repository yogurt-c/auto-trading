"""Shared pytest fixtures for all tests.

DB_PATH must be set before core.database is first imported, because engine and
SessionLocal are module-level singletons created at import time.

강제 할당(setdefault 아님): 쉘에 DB_PATH가 export되어 있거나 .env가 미리
로드된 상태에서도 반드시 테스트 전용 DB를 사용하도록 한다.
"""

import os

# Set test DB path before any core imports — 강제 override (setdefault 사용 금지)
os.environ["DB_PATH"] = "tests/data/test.db"

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.database import init_db


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Drop and re-create test DB, then run Alembic migrations."""
    db_path = os.environ.get("DB_PATH", "tests/data/test.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db()


@pytest.fixture(scope="session")
def app_client(_init_db):
    """FastAPI TestClient with test DB initialized.

    Uses TestClient without context manager to avoid triggering the lifespan
    (which starts the background scheduler — unnecessary in tests).
    """
    from app.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def auth_client(_init_db):
    """TestClient with JWT auth header (보호된 엔드포인트 테스트용).

    - bcrypt 해시를 DB에 직접 저장하여 /api/auth/login으로 토큰 획득
    - teardown에서 APP_PASSWORD_HASH DB row 삭제
    """
    import bcrypt as _bcrypt

    from app.infrastructure import repository as db
    from app.main import app

    test_password = "test-password-123"
    hashed = _bcrypt.hashpw(test_password.encode(), _bcrypt.gensalt()).decode()

    # DB에 테스트 비밀번호 해시 설정
    db.save_setting("APP_PASSWORD_HASH", hashed)

    client = TestClient(app)
    resp = client.post("/api/auth/login", json={"password": test_password})
    assert resp.status_code == 200, f"auth_client login failed: {resp.text}"
    token = resp.json()["access_token"]

    # Authorization 헤더를 포함한 클라이언트 반환 (headers 속성 덮어쓰기)
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client

    # teardown: 테스트 DB에서 비밀번호 해시 제거
    from sqlalchemy import delete as sa_delete

    from app.infrastructure.database import get_session
    from app.infrastructure.models import Setting as SettingModel

    with get_session() as s:
        s.execute(sa_delete(SettingModel).where(SettingModel.key == "APP_PASSWORD_HASH"))


@pytest.fixture
def sample_holding():
    return {"ticker": "AAPL", "shares": 10.0, "avg_price": 150.0}


@pytest.fixture
def sample_strategy():
    return {
        "name": "Test Strategy",
        "strategy_type": "value",
        "ticker": "AAPL",
        "entry_price_drop_pct": -5.0,
        "take_profit_pct": 20.0,
        "stop_loss_pct": -10.0,
    }


@pytest.fixture
def db_holding(_init_db):
    """Holding + Transaction 을 real DB에 생성하고 teardown에서 제거."""
    from app.infrastructure import repository as db

    holding = db.upsert_holding("TESTHOLD", 8.0, 200.0)
    yield holding
    db.remove_holding("TESTHOLD")


@pytest.fixture
def db_trade_log(_init_db):
    """TradeLog를 real DB에 생성하고 teardown에서 제거."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import TradeLog as TradeLogModel

    log = db.add_trade_log(
        ticker="TESTLOG",
        side="buy",
        qty=3.0,
        order_type="market",
        status="filled",
        broker_order_id="fixture-order-id",
    )
    yield log
    with get_session() as s:
        s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


@pytest.fixture
def db_partially_filled_log(_init_db):
    """partially_filled TradeLog를 real DB에 생성하고 teardown에서 제거."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import TradeLog as TradeLogModel

    log = db.add_trade_log(
        ticker="SYNCTEST",
        side="buy",
        qty=5.0,
        order_type="market",
        status="partially_filled",
        broker_order_id="partial-order-uuid-001",
    )
    yield log
    with get_session() as s:
        s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


@pytest.fixture
def db_scheduler_run(_init_db):
    """SchedulerRun을 real DB에 생성하고 teardown에서 제거."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import SchedulerRun as SchedulerRunModel

    run = db.add_scheduler_run(status="completed", summary="fixture run")
    db.update_scheduler_run(run["id"], strategies_checked=2, orders_placed=1)
    run = db.get_scheduler_runs(limit=1, offset=0)[0]
    yield run
    with get_session() as s:
        s.execute(sa_delete(SchedulerRunModel).where(SchedulerRunModel.id == run["id"]))
