"""Portfolio data access layer (SQLAlchemy ORM)."""

from __future__ import annotations

from loguru import logger
from sqlalchemy import delete, func, select, update

from .database import get_session
from .models import Holding, RealizedTrade, SchedulerRun, Setting, Strategy, TradeLog
from .timezone import now_kst

# ---------------------------------------------------------------------------
# Holdings
# ---------------------------------------------------------------------------


def get_all_holdings() -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Holding).order_by(Holding.ticker)).scalars().all()
        return [r.to_dict() for r in rows]



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


def rebuild_holdings_from_broker(positions: list[dict]) -> list[dict]:
    """KIS 전체 포지션으로 holdings 테이블을 원자적으로 재구성.

    positions 각 항목: ticker, qty, avg_entry_price, market, currency
    """
    with get_session() as s:
        existing_count = s.scalar(select(func.count()).select_from(Holding))
        if not positions and existing_count > 0:
            logger.warning(
                f"KIS returned 0 positions but DB has {existing_count} holdings — "
                "skipping rebuild (network hiccup guard). "
                "의도적으로 전량 매도했다면 다시 동기화를 실행하세요."
            )
            return get_all_holdings()
        s.execute(delete(Holding))
        for pos in positions:
            s.add(
                Holding(
                    ticker=pos["ticker"],
                    shares=pos["qty"],
                    avg_price=pos["avg_entry_price"],
                    market=pos.get("market", "US"),
                    currency=pos.get("currency", "USD"),
                )
            )
    return get_all_holdings()


# ---------------------------------------------------------------------------
# Transactions (trade_logs 기반)
# ---------------------------------------------------------------------------


def list_transactions(limit: int = 50, market: str | None = None) -> list[dict]:
    """trade_logs 기반 KR+US 전체 거래 이력 반환 (매수·매도 모두 포함).

    executed_at DESC 정렬. market 필터 선택적.
    """
    from sqlalchemy import or_

    with get_session() as s:
        q = (
            select(TradeLog)
            .where(
                or_(TradeLog.status == "filled", TradeLog.status == "accepted"),
                TradeLog.filled_price.isnot(None),
            )
            .order_by(TradeLog.executed_at.desc())
            .limit(limit)
        )
        if market:
            q = q.where(TradeLog.market == market.upper())
        dicts = [r.to_dict() for r in s.execute(q).scalars().all()]

    result = []
    for d in dicts:
        result.append(
            {
                "id": d["id"],
                "ticker": d["ticker"],
                "action": d["side"],
                "shares": d["qty"],
                "price": d["filled_price"],
                "total": round((d["qty"] or 0) * (d["filled_price"] or 0), 6),
                "executed_at": d["executed_at"].isoformat()
                if hasattr(d["executed_at"], "isoformat")
                else str(d["executed_at"]),
                "market": d["market"],
                "currency": d["currency"],
                "side": d["side"],
                "strategy_id": d["strategy_id"],
            }
        )
    return result


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
    market: str = "US",
    currency: str = "USD",
    entry_price_drop_pct: float | None = None,
    entry_rsi_below: float | None = None,
    take_profit_pct: float | None = None,
    stop_loss_pct: float | None = None,
    sell_ratio: float | None = None,
    dca_amount: float | None = None,
    dca_frequency_days: int | None = None,
    max_position: float | None = None,
    entry_bb_lower_touch: bool | None = None,
    entry_macd_hist_positive: bool | None = None,
    entry_disparity_below: float | None = None,
    entry_volume_surge: float | None = None,
    entry_sma_cross: int | None = None,
    strategy_id: int | None = None,
) -> dict:
    with get_session() as s:
        if strategy_id:
            strategy = s.get(Strategy, strategy_id)
            if strategy is None:
                raise ValueError(f"Strategy {strategy_id} not found")
        else:
            strategy = Strategy()
            s.add(strategy)

        strategy.name = name
        strategy.ticker = ticker.upper() if ticker else None
        strategy.strategy_type = strategy_type
        strategy.description = description
        strategy.ai_rationale = ai_rationale
        strategy.market = market
        strategy.currency = currency
        strategy.entry_price_drop_pct = entry_price_drop_pct
        strategy.entry_rsi_below = entry_rsi_below
        strategy.take_profit_pct = take_profit_pct
        strategy.stop_loss_pct = stop_loss_pct
        strategy.sell_ratio = sell_ratio
        strategy.dca_amount = dca_amount
        strategy.dca_frequency_days = dca_frequency_days
        strategy.max_position = max_position
        strategy.entry_bb_lower_touch = entry_bb_lower_touch
        strategy.entry_macd_hist_positive = entry_macd_hist_positive
        strategy.entry_disparity_below = entry_disparity_below
        strategy.entry_volume_surge = entry_volume_surge
        strategy.entry_sma_cross = entry_sma_cross
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


def get_strategy_by_id(strategy_id: int) -> dict | None:
    """ID로 전략 단건 조회 (O(1))."""
    with get_session() as s:
        strategy = s.get(Strategy, strategy_id)
        return strategy.to_dict() if strategy else None


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
    filled_price: float | None = None,
    broker_order_id: str | None = None,
    market: str = "US",
    currency: str = "USD",
    ai_reasoning: str | None = None,
    avg_cost_snapshot: float | None = None,
) -> dict:
    with get_session() as s:
        log = TradeLog(
            ticker=ticker.upper(),
            side=side,
            qty=qty,
            order_type=order_type,
            status=status,
            strategy_id=strategy_id,
            limit_price=limit_price,
            filled_price=filled_price,
            broker_order_id=broker_order_id,
            market=market,
            currency=currency,
            ai_reasoning=ai_reasoning,
            avg_cost_snapshot=avg_cost_snapshot,
        )
        s.add(log)
        s.flush()
        result = log.to_dict()

    if strategy_id and status != "failed":
        update_strategy_last_triggered(strategy_id)

    return result


def add_realized_trade(
    trade_log_id: int,
    ticker: str,
    qty: float,
    sell_price: float,
    avg_cost: float,
    realized_pnl: float,
    realized_pnl_pct: float,
    currency: str,
    strategy_id: int | None = None,
) -> dict:
    with get_session() as s:
        rt = RealizedTrade(
            trade_log_id=trade_log_id,
            ticker=ticker.upper(),
            qty=qty,
            sell_price=sell_price,
            avg_cost=avg_cost,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            currency=currency,
            strategy_id=strategy_id,
        )
        s.add(rt)
        s.flush()
        return rt.to_dict()


def upsert_realized_trade_by_trade_log_id(
    trade_log_id: int,
    ticker: str,
    qty: float,
    sell_price: float,
    avg_cost: float,
    realized_pnl: float,
    realized_pnl_pct: float,
    currency: str,
    strategy_id: int | None = None,
) -> tuple[str, int]:
    """trade_log_id 기준 realized_trade INSERT OR IGNORE.

    Returns: ("inserted" | "unchanged", row_id)
    """
    with get_session() as s:
        existing = s.execute(
            select(RealizedTrade).where(RealizedTrade.trade_log_id == trade_log_id)
        ).scalar_one_or_none()
        if existing:
            return ("unchanged", existing.id)
        rt = RealizedTrade(
            trade_log_id=trade_log_id,
            ticker=ticker.upper(),
            qty=qty,
            sell_price=sell_price,
            avg_cost=avg_cost,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            currency=currency,
            strategy_id=strategy_id,
        )
        s.add(rt)
        s.flush()
        return ("inserted", rt.id)


def list_orphan_sell_logs() -> list[dict]:
    """realized_trade 없는 완료된 매도 trade_log 반환.

    조건: side=sell, status=filled, filled_price IS NOT NULL, avg_cost_snapshot IS NOT NULL,
          대응하는 realized_trades 행 없음.
    """
    with get_session() as s:
        existing_log_ids = s.execute(select(RealizedTrade.trade_log_id)).scalars().all()
        q = select(TradeLog).where(
            TradeLog.side == "sell",
            TradeLog.status == "filled",
            TradeLog.filled_price.isnot(None),
            TradeLog.avg_cost_snapshot.isnot(None),
            TradeLog.id.notin_(existing_log_ids) if existing_log_ids else True,
        )
        rows = s.execute(q).scalars().all()
        return [r.to_dict() for r in rows]


def get_realized_trades(start_date: str, end_date: str) -> list[dict]:
    with get_session() as s:
        rows = (
            s.execute(
                select(RealizedTrade)
                .where(
                    func.date(RealizedTrade.executed_at) >= start_date,
                    func.date(RealizedTrade.executed_at) <= end_date,
                )
                .order_by(RealizedTrade.executed_at.asc())
            )
            .scalars()
            .all()
        )
        return [r.to_dict() for r in rows]


def get_pending_fill_logs() -> list[dict]:
    """broker_order_id가 있는 미체결(partially_filled / accepted) 거래 로그 반환.

    - partially_filled: 일부만 체결된 주문
    - accepted: 국내 주문에서 polling 윈도우 내 체결 미확인 주문 (이후 체결됐을 수 있음)
    """
    with get_session() as s:
        from sqlalchemy import or_

        rows = (
            s.execute(
                select(TradeLog).where(
                    or_(
                        TradeLog.status == "partially_filled",
                        TradeLog.status == "accepted",
                    ),
                    TradeLog.broker_order_id.isnot(None),
                )
            )
            .scalars()
            .all()
        )
        return [r.to_dict() for r in rows]


def get_partially_filled_logs() -> list[dict]:
    """하위 호환용 별칭. get_pending_fill_logs()를 사용하세요."""
    return get_pending_fill_logs()


def update_trade_log_status(log_id: int, status: str, filled_price: float | None = None) -> None:
    """거래 로그 상태 및 체결가 업데이트."""
    with get_session() as s:
        log = s.get(TradeLog, log_id)
        if log:
            log.status = status
            if filled_price is not None:
                log.filled_price = filled_price
            s.flush()


def get_trade_logs(limit: int = 50, offset: int = 0) -> list[dict]:
    with get_session() as s:
        rows = (
            s.execute(
                select(TradeLog).order_by(TradeLog.executed_at.desc()).offset(offset).limit(limit)
            )
            .scalars()
            .all()
        )
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
            update(Strategy).where(Strategy.id.in_(strategy_ids)).values(last_checked_at=now_kst())
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
        rows = (
            s.execute(
                select(SchedulerRun)
                .order_by(SchedulerRun.started_at.desc())
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )
        return [r.to_dict() for r in rows]


def count_scheduler_runs() -> int:
    with get_session() as s:
        return s.scalar(select(func.count()).select_from(SchedulerRun))
