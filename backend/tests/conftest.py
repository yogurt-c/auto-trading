"""Shared pytest fixtures for all tests.

DB_PATH must be set before core.database is first imported, because engine and
SessionLocal are module-level singletons created at import time.
"""

import os

# Set test DB path before any core imports
os.environ.setdefault("DB_PATH", "backend/tests/data/test.db")

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.database import init_db


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Run Alembic migrations once for the entire test session."""
    init_db()


@pytest.fixture(scope="session")
def app_client(_init_db):
    """FastAPI TestClient with test DB initialized.

    Uses TestClient without context manager to avoid triggering the lifespan
    (which starts the background scheduler — unnecessary in tests).
    """
    from app.main import app

    return TestClient(app)


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
    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import TradeLog as TradeLogModel
    from sqlalchemy import delete as sa_delete

    log = db.add_trade_log(
        ticker="TESTLOG",
        side="buy",
        qty=3.0,
        order_type="market",
        status="filled",
        alpaca_id="fixture-order-id",
    )
    yield log
    with get_session() as s:
        s.execute(sa_delete(TradeLogModel).where(TradeLogModel.id == log["id"]))


@pytest.fixture
def db_scheduler_run(_init_db):
    """SchedulerRun을 real DB에 생성하고 teardown에서 제거."""
    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import SchedulerRun as SchedulerRunModel
    from sqlalchemy import delete as sa_delete

    run = db.add_scheduler_run(status="completed", summary="fixture run")
    db.update_scheduler_run(run["id"], strategies_checked=2, orders_placed=1)
    run = db.get_scheduler_runs(limit=1, offset=0)[0]
    yield run
    with get_session() as s:
        s.execute(sa_delete(SchedulerRunModel).where(SchedulerRunModel.id == run["id"]))
