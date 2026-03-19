"""Portfolio data access layer (SQLAlchemy ORM)."""

from __future__ import annotations

from sqlalchemy import delete, func, select, update

from .database import get_session
from .models import Holding, SchedulerRun, Setting, Strategy, TradeLog, Transaction
from .timezone import now_kst

# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------

def get_all_holdings() -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Holding).order_by(Holding.ticker)).scalars().all()
        return [r.to_dict() for r in rows]


def upsert_holding(ticker: str, shares: float, avg_price: float) -> dict:
    """Add shares or update via weighted average."""
    ticker = ticker.upper()
    with get_session() as s:
        existing = s.execute(select(Holding).where(Holding.ticker == ticker)).scalar_one_or_none()

        if existing:
            new_total = existing.shares + shares
            new_avg = (existing.avg_price * existing.shares + avg_price * shares) / new_total
            existing.shares = new_total
            existing.avg_price = new_avg
            holding = existing
        else:
            holding = Holding(ticker=ticker, shares=shares, avg_price=avg_price)
            s.add(holding)

        s.add(Transaction(
            ticker=ticker, action="buy",
            shares=shares, price=avg_price, total=shares * avg_price,
        ))
        s.flush()
        return holding.to_dict()


def update_holding(ticker: str, shares: float, avg_price: float) -> dict | None:
    """Overwrite shares and avg_price directly."""
    ticker = ticker.upper()
    with get_session() as s:
        holding = s.execute(select(Holding).where(Holding.ticker == ticker)).scalar_one_or_none()
        if not holding:
            return None
        holding.shares = shares
        holding.avg_price = avg_price
        s.flush()
        return holding.to_dict()


def remove_holding(ticker: str) -> bool:
    with get_session() as s:
        holding = s.execute(
            select(Holding).where(Holding.ticker == ticker.upper())
        ).scalar_one_or_none()
        if not holding:
            return False
        s.delete(holding)
        return True


def rebuild_holdings_from_alpaca(positions: list[dict]) -> list[dict]:
    """Alpaca 전체 포지션으로 holdings 테이블을 원자적으로 재구성."""
    with get_session() as s:
        s.execute(delete(Holding))
        for pos in positions:
            s.add(Holding(
                ticker=pos["ticker"],
                shares=pos["qty"],
                avg_price=pos["avg_entry_price"],
            ))
        s.commit()
    return get_all_holdings()


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def get_transactions(ticker: str | None = None, limit: int = 100) -> list[dict]:
    with get_session() as s:
        q = select(Transaction).order_by(Transaction.executed_at.desc()).limit(limit)
        if ticker:
            q = q.where(Transaction.ticker == ticker.upper())
        return [r.to_dict() for r in s.execute(q).scalars().all()]


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def get_strategies(status: str | None = None) -> list[dict]:
    with get_session() as s:
        q = select(Strategy).order_by(Strategy.created_at.desc())
        if status:
            q = q.where(Strategy.status == status)
        return [r.to_dict() for r in s.execute(q).scalars().all()]


def save_strategy(
    name: str,
    strategy_type: str,
    description: str = "",
    ticker: str | None = None,
    ai_rationale: str | None = None,
    entry_price_drop_pct: float | None = None,
    entry_rsi_below: float | None = None,
    take_profit_pct: float | None = None,
    stop_loss_pct: float | None = None,
    sell_ratio: float | None = None,
    dca_amount_usd: float | None = None,
    dca_frequency_days: int | None = None,
    max_position_usd: float | None = None,
    strategy_id: int | None = None,
) -> dict:
    with get_session() as s:
        if strategy_id:
            strategy = s.get(Strategy, strategy_id)
        else:
            strategy = Strategy()
            s.add(strategy)

        strategy.name = name
        strategy.ticker = ticker.upper() if ticker else None
        strategy.strategy_type = strategy_type
        strategy.description = description
        strategy.ai_rationale = ai_rationale
        strategy.entry_price_drop_pct = entry_price_drop_pct
        strategy.entry_rsi_below = entry_rsi_below
        strategy.take_profit_pct = take_profit_pct
        strategy.stop_loss_pct = stop_loss_pct
        strategy.sell_ratio = sell_ratio
        strategy.dca_amount_usd = dca_amount_usd
        strategy.dca_frequency_days = dca_frequency_days
        strategy.max_position_usd = max_position_usd
        s.flush()
        return strategy.to_dict()


def update_strategy_status(strategy_id: int, status: str) -> dict | None:
    with get_session() as s:
        strategy = s.get(Strategy, strategy_id)
        if not strategy:
            return None
        strategy.status = status
        s.flush()
        return strategy.to_dict()


def delete_strategy(strategy_id: int) -> bool:
    with get_session() as s:
        strategy = s.get(Strategy, strategy_id)
        if not strategy:
            return False
        s.delete(strategy)
        return True


# ---------------------------------------------------------------------------
# Trade logs
# ---------------------------------------------------------------------------

def add_trade_log(
    ticker: str,
    side: str,
    qty: float,
    order_type: str,
    status: str,
    strategy_id: int | None = None,
    limit_price: float | None = None,
    alpaca_id: str | None = None,
    ai_reasoning: str | None = None,
) -> dict:
    with get_session() as s:
        log = TradeLog(
            ticker=ticker.upper(), side=side, qty=qty,
            order_type=order_type, status=status,
            strategy_id=strategy_id, limit_price=limit_price,
            alpaca_id=alpaca_id, ai_reasoning=ai_reasoning,
        )
        s.add(log)
        s.flush()
        result = log.to_dict()

    if strategy_id and status != "failed":
        update_strategy_last_triggered(strategy_id)

    return result


def get_trade_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(TradeLog).order_by(TradeLog.executed_at.desc()).offset(offset).limit(limit)
        ).scalars().all()
        return [r.to_dict() for r in rows]


def count_trade_logs() -> int:
    with get_session() as s:
        return s.scalar(select(func.count()).select_from(TradeLog))


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_setting(key: str) -> str | None:
    with get_session() as s:
        row = s.get(Setting, key)
        return row.value if row else None


def save_setting(key: str, value: str) -> None:
    with get_session() as s:
        row = s.get(Setting, key)
        if row:
            row.value = value
        else:
            s.add(Setting(key=key, value=value))


def get_all_settings() -> dict[str, str]:
    with get_session() as s:
        rows = s.execute(select(Setting)).scalars().all()
        return {r.key: r.value for r in rows}


# ---------------------------------------------------------------------------
# Strategy timestamps
# ---------------------------------------------------------------------------

def update_strategies_last_checked(strategy_ids: list[int]) -> None:
    if not strategy_ids:
        return
    with get_session() as s:
        s.execute(
            update(Strategy)
            .where(Strategy.id.in_(strategy_ids))
            .values(last_checked_at=now_kst())
        )


def update_strategy_last_triggered(strategy_id: int) -> None:
    with get_session() as s:
        strategy = s.get(Strategy, strategy_id)
        if strategy:
            strategy.last_triggered_at = now_kst()
            s.flush()


# ---------------------------------------------------------------------------
# Scheduler runs
# ---------------------------------------------------------------------------

def add_scheduler_run(
    status: str = "running", finished_at=None, summary: str | None = None
) -> dict:
    with get_session() as s:
        run = SchedulerRun(
            status=status,
            strategies_checked=0,
            orders_placed=0,
            finished_at=finished_at,
            summary=summary,
        )
        s.add(run)
        s.flush()
        return run.to_dict()


def update_scheduler_run(run_id: int, **fields) -> None:
    with get_session() as s:
        run = s.get(SchedulerRun, run_id)
        if run:
            for key, value in fields.items():
                setattr(run, key, value)
            s.flush()


def get_scheduler_runs(limit: int = 20, offset: int = 0) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            select(SchedulerRun)
            .order_by(SchedulerRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).scalars().all()
        return [r.to_dict() for r in rows]


def count_scheduler_runs() -> int:
    with get_session() as s:
        return s.scalar(select(func.count()).select_from(SchedulerRun))
