"""SQLAlchemy engine and session factory."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _get_db_url() -> str:
    db_path = os.environ.get("DB_PATH")
    if not db_path:
        raise RuntimeError("DB_PATH 환경변수가 설정되지 않았습니다")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def _make_engine():
    return create_engine(
        _get_db_url(),
        connect_args={"check_same_thread": False},
        echo=False,
    )


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Run Alembic migrations to bring DB schema up to date."""
    from alembic.config import Config

    from alembic import command

    db_url = _get_db_url()
    alembic_ini = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
