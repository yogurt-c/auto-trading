"""SQLAlchemy engine and session factory."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def _get_db_url() -> str:
    import os
    db_path = os.environ["DB_PATH"]
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
def get_session() -> Session:
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
    from alembic import command
    from alembic.config import Config

    db_url = _get_db_url()
    alembic_ini = Path(__file__).resolve().parent.parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(cfg, "head")
