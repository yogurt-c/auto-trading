"""Agent tool definitions.

Each function here corresponds to a tool the agent can call.
Tool schemas (for Anthropic tool_use) are also defined here.
"""

from __future__ import annotations

import threading
from typing import Any

import yfinance as yf
from loguru import logger

from app.application.scheduler import is_krx_open, is_nyse_open
from app.domain.portfolio.services import PortfolioValuationService, RealizedPnlAggregator
from app.domain.trading_strategy.services import (
    DcaScheduleChecker,
    StrategyEvaluator,
    StrategyValidator,
)
from app.domain.trading_strategy.value_objects import ValidationSeverity, ValidationWarning
from app.infrastructure import kis_client
from app.infrastructure import market as market_module
from app.infrastructure import repository as db

_strategy_validator = StrategyValidator()
_strategy_evaluator = StrategyEvaluator()
_dca_checker = DcaScheduleChecker()
_valuation_service = PortfolioValuationService()
_pnl_aggregator = RealizedPnlAggregator()

# place_order는 체크 → 주문 사이에 TOCTOU 경쟁이 발생하지 않도록 직렬화
_order_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_portfolio() -> dict:
    """Return the full portfolio: all holdings with metadata."""
    holdings = db.get_all_holdings()
    return {"holdings": holdings, "count": len(holdings)}


def sync_holdings() -> dict:
    """KIS 전체 포지션으로 holdings 테이블을 즉시 재구성."""
    try:
        positions = kis_client.sync_positions()
        logger.info(f"holdings synced from KIS: {len(positions)} positions")
        return {"success": True, "synced_count": len(positions), "holdings": positions}
    except Exception as e:
        logger.warning(f"KIS sync failed, holdings unchanged: {e}")
        return {"success": False, "error": str(e)}


def get_strategies(status: str | None = None) -> dict:
    """
    Return saved trading strategies.
    status: 'active' | 'paused' | 'completed' | None (all)
    """
    strategies = db.get_strategies(status)
    return {"strategies": strategies, "count": len(strategies)}


def _validate_strategy_params(
    strategy_type: str,
    entry_price_drop_pct: float | None,
    entry_rsi_below: float | None,
    take_profit_pct: float | None,
    stop_loss_pct: float | None,
    sell_ratio: float | None,
    dca_amount: float | None,
    dca_frequency_days: int | None,
    max_position: float | None,
    entry_bb_lower_touch: bool | None = None,
    entry_macd_hist_positive: bool | None = None,
    entry_disparity_below: float | None = None,
    entry_volume_surge: float | None = None,
    entry_sma_cross: int | None = None,
) -> list[ValidationWarning]:
    """전략 파라미터 충돌·범위 검증. severity 포함 ValidationWarning 목록 반환."""
    return _strategy_validator.validate(
        strategy_type=strategy_type,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount=dca_amount,
        dca_frequency_days=dca_frequency_days,
        max_position=max_position,
        entry_bb_lower_touch=entry_bb_lower_touch,
        entry_macd_hist_positive=entry_macd_hist_positive,
        entry_disparity_below=entry_disparity_below,
        entry_volume_surge=entry_volume_surge,
        entry_sma_cross=entry_sma_cross,
    )


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
    """Save or update a trading strategy in the database."""
    # ticker로 market/currency 자동 추론 (AI가 잘못된 값을 전달한 경우 보정)
    if ticker:
        inferred_market = kis_client.ticker_market(ticker)
        inferred_currency = kis_client.ticker_currency(ticker)
        if market != inferred_market:
            logger.warning(
                f"save_strategy: market mismatch for {ticker} "
                f"(given={market}, inferred={inferred_market}) — using inferred"
            )
            market = inferred_market
            currency = inferred_currency

    all_validations = _validate_strategy_params(
        strategy_type=strategy_type,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount=dca_amount,
        dca_frequency_days=dca_frequency_days,
        max_position=max_position,
        entry_bb_lower_touch=entry_bb_lower_touch,
        entry_macd_hist_positive=entry_macd_hist_positive,
        entry_disparity_below=entry_disparity_below,
        entry_volume_surge=entry_volume_surge,
        entry_sma_cross=entry_sma_cross,
    )
    errors = [w for w in all_validations if w.severity == ValidationSeverity.ERROR]
    soft_warnings = [w for w in all_validations if w.severity == ValidationSeverity.WARNING]

    for w in all_validations:
        if w.severity == ValidationSeverity.ERROR:
            logger.error(f"[error] save_strategy blocked: {w.message}")
        else:
            logger.warning(f"[warning] save_strategy: {w.message}")

    if errors:
        return {
            "success": False,
            "errors": [e.message for e in errors],
            "warnings": [w.message for w in soft_warnings],
        }

    result = db.save_strategy(
        name=name,
        strategy_type=strategy_type,
        description=description,
        ticker=ticker,
        ai_rationale=ai_rationale,
        market=market,
        currency=currency,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount=dca_amount,
        dca_frequency_days=dca_frequency_days,
        max_position=max_position,
        entry_bb_lower_touch=entry_bb_lower_touch,
        entry_macd_hist_positive=entry_macd_hist_positive,
        entry_disparity_below=entry_disparity_below,
        entry_volume_surge=entry_volume_surge,
        entry_sma_cross=entry_sma_cross,
        strategy_id=strategy_id,
    )
    action = "updated" if strategy_id else "created"
    logger.info(f"strategy {action}: id={result.get('id')} name={name!r} type={strategy_type}")
    return {"success": True, "strategy": result, "warnings": [w.message for w in soft_warnings]}


def update_strategy_status(strategy_id: int, status: str) -> dict:
    """Update strategy status: 'active' | 'paused' | 'completed'."""
    result = db.update_strategy_status(strategy_id, status)
    if result:
        return {"success": True, "strategy": result}
    return {"success": False, "error": f"Strategy {strategy_id} not found"}


def _to_yf_ticker(ticker: str) -> str:
    """KIS 종목코드 → yfinance 티커 변환.

    국내(6자리 숫자): '.KS'(KOSPI) 시도 후 데이터 없으면 '.KQ'(KOSDAQ) 폴백.
    해외: 그대로 사용.
    """
    if not kis_client.is_korean_ticker(ticker):
        return ticker

    # KOSPI 먼저 시도
    ks_ticker = f"{ticker}.KS"
    try:
        data = yf.download(ks_ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        if not data.empty:
            return ks_ticker
    except Exception:
        pass

    # KOSDAQ 폴백
    return f"{ticker}.KQ"


def evaluate_strategy(strategy_id: int) -> dict:
    """
    전략의 진입/청산 조건을 현재가 기준으로 평가.
    - entry_price_drop_pct: 30일 고점 대비 하락률
    - entry_rsi_below: 14일 RSI 계산
    - take_profit_pct / stop_loss_pct: 보유 평균단가 대비 수익률
    """
    strategy = db.get_strategy_by_id(strategy_id)
    if strategy is None:
        return {"error": f"Strategy {strategy_id} not found"}

    ticker = strategy.get("ticker")
    if not ticker:
        return {"error": "Strategy has no ticker set"}

    yf_ticker = _to_yf_ticker(ticker)
    market = strategy.get("market", "US")
    currency = strategy.get("currency", "USD")

    try:
        mkt = market_module.fetch_market_data(
            ticker=ticker,
            market=market,
            currency=currency,
            yf_ticker=yf_ticker,
        )
    except Exception as e:
        return {"error": f"Failed to fetch market data for {ticker} ({yf_ticker}): {e}"}

    # I/O: current holding from DB
    holdings = db.get_all_holdings()
    current_holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)

    result = _strategy_evaluator.evaluate(strategy, mkt, current_holding)

    result_dict = result.model_dump()

    # max_position 한도 초과 시 entry_triggered 차단 (place_order까지 도달하지 않도록)
    max_position = strategy.get("max_position")
    if max_position and result_dict["entry_triggered"]:
        strategy_currency = strategy.get("currency", "USD")
        # 통화 단위 일관성 검증
        if mkt.currency and mkt.currency != strategy_currency:
            logger.warning(
                f"evaluate_strategy id={strategy_id}: currency mismatch — "
                f"strategy={strategy_currency}, market_data={mkt.currency}"
            )
            result_dict["note"] = (
                f"통화 단위 불일치 경고: 전략={strategy_currency}, 시장데이터={mkt.currency}. "
                "max_position 한도 체크 결과가 부정확할 수 있습니다."
            )
        current_qty = current_holding.get("shares", 0) if current_holding else 0
        current_value = current_qty * mkt.current_price
        if current_value >= max_position:
            result_dict["entry_triggered"] = False
            result_dict["note"] = (
                f"포지션 한도 초과로 매수 차단: "
                f"현재 {current_value:,.0f} >= 한도 {max_position:,.0f} {strategy_currency}"
            )
            logger.info(
                f"evaluate_strategy id={strategy_id}: entry blocked — "
                f"position {current_value:,.0f} >= "
                f"max_position {max_position:,.0f} {strategy_currency}"
            )

    logger.debug(
        f"evaluate_strategy id={strategy_id}: "
        f"entry={result_dict['entry_triggered']}, exit={result_dict['exit_triggered']}"
    )
    return result_dict


def get_broker_account() -> dict:
    """Return KIS account info and open positions."""
    try:
        account = kis_client.get_account()
        positions = kis_client.get_positions()
        return {"account": account, "positions": positions}
    except Exception as e:
        return {"error": str(e)}


def check_dca_due(strategy_id: int) -> dict:
    """
    DCA 전략의 다음 매수 시점이 됐는지 코드로 판단.
    - dca_frequency_days가 없으면 DCA 전략이 아님
    - last_triggered_at이 None이면 한 번도 실행 안 됐으므로 즉시 실행
    - (now - last_triggered_at) >= dca_frequency_days 이면 실행
    """
    strategy = db.get_strategy_by_id(strategy_id)
    if strategy is None:
        return {"error": f"Strategy {strategy_id} not found"}

    result = _dca_checker.is_due(strategy)
    logger.debug(
        f"check_dca_due id={strategy_id}: is_due={result.get('is_due')}, {result.get('reason')}"
    )
    return result


def get_scheduler_runs(limit: int = 10) -> dict:
    """최근 스케줄러 실행 이력 반환. Trade Executor가 과거 실행 결과를 참고해 판단에 활용."""
    runs = db.get_scheduler_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}


def get_performance(start_date: str, end_date: str, group_by: str = "day") -> dict:
    """기간 내 실현 손익 집계 반환."""
    realized = db.get_realized_trades(start_date, end_date)
    strategies = db.get_strategies()
    strategy_names = {s["id"]: s["name"] for s in strategies}
    summary = _pnl_aggregator.aggregate(realized, strategy_names, start_date, end_date, group_by)
    return {
        "period_start": summary.period_start,
        "period_end": summary.period_end,
        "total_realized_pnl": summary.total_realized_pnl,
        "total_trade_count": summary.total_trade_count,
        "win_count": summary.win_count,
        "win_rate": summary.win_rate,
        "trades": [t.model_dump() for t in summary.trades],
        "by_period": [p.model_dump() for p in summary.by_period],
        "by_strategy": [s.model_dump() for s in summary.by_strategy],
    }


def _sync_from_broker() -> str:
    """주문 완료 후 KIS 전체 포지션으로 holdings를 재구성."""
    try:
        positions = kis_client.sync_positions()
        logger.info(f"holdings synced from KIS: {len(positions)} positions")
        return f"synced {len(positions)} positions from KIS"
    except Exception as e:
        logger.warning(f"KIS sync failed, holdings unchanged: {e}")
        return f"sync failed: {e}"


def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
    strategy_id: int | None = None,
    ai_reasoning: str | None = None,
    max_position: float | None = None,
) -> dict:
    """
    Place a buy or sell order via KIS and log it.
    side: 'buy' | 'sell'
    order_type: 'market' | 'limit'
    max_position: if set, rejects buy orders exceeding this size (strategy currency 단위)

    _order_lock으로 직렬화하여 max_position 체크 → 주문 제출 사이의 TOCTOU 경쟁을 방지.
    """
    with _order_lock:
        return _place_order_locked(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            limit_price=limit_price,
            strategy_id=strategy_id,
            ai_reasoning=ai_reasoning,
            max_position=max_position,
        )


def _place_order_locked(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
    strategy_id: int | None = None,
    ai_reasoning: str | None = None,
    max_position: float | None = None,
) -> dict:
    market = kis_client.ticker_market(ticker)
    currency = kis_client.ticker_currency(ticker)

    # 시장 시간 검증 — 장 외 시간 주문 차단
    if market == "KR" and not is_krx_open():
        logger.warning(f"order rejected — KRX closed: ticker={ticker}")
        return {
            "success": False,
            "error": "장 외 시간: KR 시장은 KST 09:00-15:30에만 주문 가능합니다",
        }
    if market == "US" and not is_nyse_open():
        logger.warning(f"order rejected — NYSE closed: ticker={ticker}")
        return {
            "success": False,
            "error": "장 외 시간: US 시장은 ET 09:30-16:00에만 주문 가능합니다",
        }

    # max_position 한도 검증 (매수 시에만)
    if max_position and side.lower() == "buy":
        check_price = limit_price
        if check_price is None:
            prices = market_module.get_current_prices([ticker.upper()])
            check_price = prices.get(ticker.upper())

        if check_price:
            holdings = db.get_all_holdings()
            holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)
            current_value = (holding["shares"] * check_price) if holding else 0.0
            order_value = qty * check_price
            projected_value = current_value + order_value

            if projected_value > max_position:
                detail = (
                    f"현재 {current_value:,.0f} + 신규 {order_value:,.0f} "
                    f"= {projected_value:,.0f} (한도 {max_position:,.0f} {currency})"
                )
                logger.warning(f"order rejected — max_position exceeded: {detail}")
                return {
                    "success": False,
                    "error": f"max_position 한도 초과: {detail}",
                }

    # 매도 시 avg_cost 미리 조회
    avg_cost: float | None = None
    if side.lower() == "sell":
        holdings = db.get_all_holdings()
        holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)
        avg_cost = holding["avg_price"] if holding else None

    try:
        order = kis_client.place_order(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            limit_price=limit_price,
        )
        filled_price: float | None = order.get("filled_avg_price")
        log = db.add_trade_log(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            status=order["status"],
            strategy_id=strategy_id,
            limit_price=limit_price,
            filled_price=filled_price,
            broker_order_id=order.get("broker_order_id"),
            market=market,
            currency=currency,
            ai_reasoning=ai_reasoning,
            avg_cost_snapshot=avg_cost if side.lower() == "sell" else None,
        )

        # 매도 체결 시 실현 손익 스냅샷 저장
        if (
            side.lower() == "sell"
            and order["status"] == "filled"
            and avg_cost is not None
            and filled_price is not None
            and filled_price > 0
        ):
            pnl = (filled_price - avg_cost) * qty
            pnl_pct = round((pnl / (avg_cost * qty) * 100) if avg_cost else 0.0, 2)
            db.add_realized_trade(
                trade_log_id=log["id"],
                ticker=ticker,
                qty=qty,
                sell_price=filled_price,
                avg_cost=avg_cost,
                realized_pnl=pnl,
                realized_pnl_pct=pnl_pct,
                currency=currency,
                strategy_id=strategy_id,
            )
            logger.info(
                f"realized_trade saved: {ticker} qty={qty} "
                f"sell={filled_price} cost={avg_cost} pnl={pnl:.2f} {currency}"
            )

        # holdings DB 동기화
        holdings_synced = _sync_from_broker()
        logger.info(f"place_order success: {side} {qty} {ticker}, sync={holdings_synced}")

        return {
            "success": True,
            "order": order,
            "log_id": log["id"],
            "holdings_synced": holdings_synced,
        }
    except Exception as e:
        logger.error(f"place_order failed: {ticker} {side} — {e}")
        db.add_trade_log(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            status="failed",
            strategy_id=strategy_id,
            limit_price=limit_price,
            market=market,
            currency=currency,
            ai_reasoning=f"Error: {e}",
        )
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Pending order sync
# ---------------------------------------------------------------------------


def sync_pending_orders() -> int:
    """partially_filled 주문을 KIS에서 현재 상태로 갱신. 업데이트된 건수 반환."""
    logs = db.get_partially_filled_logs()
    updated = 0
    for log in logs:
        try:
            order = kis_client.get_order(
                log["broker_order_id"],
                market=log.get("market", "US"),
            )
            new_status = order["status"]
            if new_status != "partially_filled":
                filled_price = order.get("filled_avg_price")
                db.update_trade_log_status(
                    log["id"],
                    status=new_status,
                    filled_price=filled_price,
                )
                logger.info(
                    f"trade_log {log['id']} {log['ticker']} {log['side']}: "
                    f"partially_filled → {new_status}"
                )

                # 매도 체결 시 realized_trade 생성
                avg_cost_snap = log.get("avg_cost_snapshot")
                if (
                    new_status == "filled"
                    and log["side"].lower() == "sell"
                    and filled_price is not None
                    and filled_price > 0
                    and avg_cost_snap is not None
                ):
                    qty = log["qty"]
                    pnl = (filled_price - avg_cost_snap) * qty
                    pnl_pct = round(pnl / (avg_cost_snap * qty) * 100, 2)
                    db.add_realized_trade(
                        trade_log_id=log["id"],
                        ticker=log["ticker"],
                        qty=qty,
                        sell_price=filled_price,
                        avg_cost=avg_cost_snap,
                        realized_pnl=pnl,
                        realized_pnl_pct=pnl_pct,
                        currency=log.get("currency", "USD"),
                        strategy_id=log.get("strategy_id"),
                    )
                    logger.info(
                        f"realized_trade (deferred): {log['ticker']} qty={qty} "
                        f"sell={filled_price} cost={avg_cost_snap} pnl={pnl:.2f}"
                    )

                updated += 1
        except Exception as e:
            logger.warning(f"sync order {log.get('broker_order_id')} failed: {e}")
    return updated


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_MAP = {
    "get_portfolio": get_portfolio,
    "sync_holdings": sync_holdings,
    "get_strategies": get_strategies,
    "save_strategy": save_strategy,
    "update_strategy_status": update_strategy_status,
    "evaluate_strategy": evaluate_strategy,
    "get_broker_account": get_broker_account,
    "place_order": place_order,
    "check_dca_due": check_dca_due,
    "get_scheduler_runs": get_scheduler_runs,
}


def dispatch_tool(name: str, inputs: dict) -> Any:
    """Execute a tool by name with the given inputs dict."""
    fn = TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(**inputs)
    except Exception as e:
        logger.error(f"tool '{name}' raised an exception: {e}")
        return {"error": f"Tool '{name}' failed: {e}"}


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------

PORTFOLIO_TOOLS = [
    {
        "name": "get_portfolio",
        "description": "Return all holdings in the portfolio with ticker, shares, avg_price, market, currency, created_at.",  # noqa: E501
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sync_holdings",
        "description": (
            "Sync holdings table from KIS positions (single source of truth). "
            "Call this to get the latest holdings before analysis."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

STRATEGY_TOOLS = [
    {
        "name": "get_strategies",
        "description": "Return saved trading strategies. Filter by status if provided.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed"],
                    "description": "Filter by strategy status (omit for all)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "save_strategy",
        "description": (
            "Save or update a trading strategy. Use this after discussing a strategy with the user "
            "to persist the agreed-upon parameters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Human-readable strategy name"},
                "strategy_type": {
                    "type": "string",
                    "enum": ["dca", "momentum", "value", "stop_loss", "take_profit", "custom"],
                },
                "description": {
                    "type": "string",
                    "description": "Description of the strategy agreed with user",
                },
                "ticker": {
                    "type": "string",
                    "description": "Target ticker. 국내: 6자리 숫자(005930), 미국: 영문(AAPL)",
                },
                "ai_rationale": {
                    "type": "string",
                    "description": "AI's reasoning for this strategy",
                },
                "market": {
                    "type": "string",
                    "enum": ["KR", "US"],
                    "description": "시장 구분. ticker가 6자리 숫자이면 KR, 영문이면 US",
                },
                "currency": {
                    "type": "string",
                    "enum": ["KRW", "USD"],
                    "description": "금액 단위. KR 시장은 KRW, US 시장은 USD",
                },
                "entry_price_drop_pct": {
                    "type": "number",
                    "description": "Buy trigger: % drop from 30d high (negative, e.g. -5.0)",
                },
                "entry_rsi_below": {
                    "type": "number",
                    "description": "Buy trigger: RSI threshold (e.g. 30)",
                },
                "take_profit_pct": {
                    "type": "number",
                    "description": "Sell trigger: target profit % (e.g. 20.0)",
                },
                "stop_loss_pct": {
                    "type": "number",
                    "description": "Sell trigger: stop loss % (e.g. -10.0)",
                },
                "sell_ratio": {
                    "type": "number",
                    "description": "Fraction of position to sell (0.5 = half)",
                },
                "dca_amount": {
                    "type": "number",
                    "description": "매수 금액 (currency 단위). KR이면 KRW, US이면 USD",
                },
                "dca_frequency_days": {"type": "integer", "description": "DCA interval in days"},
                "max_position": {
                    "type": "number",
                    "description": "최대 포지션 한도 (currency 단위). KR이면 KRW, US이면 USD",
                },
                "entry_bb_lower_touch": {
                    "type": "boolean",
                    "description": "Buy trigger: true이면 현재가가 볼린저 하단 이하일 때 진입",
                },
                "entry_macd_hist_positive": {
                    "type": "boolean",
                    "description": "Buy trigger: MACD 히스토그램이 양수일 때 진입",
                },
                "entry_disparity_below": {
                    "type": "number",
                    "description": "Buy trigger: 이격도(%) 임계값 이하 시 진입 (음수, 예: -5.0)",
                },
                "entry_volume_surge": {
                    "type": "number",
                    "description": "Buy trigger: 거래량 비율 임계값 초과 시 진입 (예: 2.0)",
                },
                "entry_sma_cross": {
                    "type": "integer",
                    "enum": [20, 60],
                    "description": "Buy trigger: 현재가가 SMA(N) 위에 있을 때 진입",
                },
                "strategy_id": {
                    "type": "integer",
                    "description": "Existing strategy ID to update (omit to create new)",
                },
            },
            "required": ["name", "strategy_type"],
        },
    },
    {
        "name": "update_strategy_status",
        "description": "Activate, pause, or complete an existing strategy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {"type": "integer", "description": "Strategy ID"},
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed"],
                },
            },
            "required": ["strategy_id", "status"],
        },
    },
]

TRADE_TOOLS = [
    {
        "name": "get_scheduler_runs",
        "description": (
            "Return recent scheduler execution history. "
            "Use this first to understand past execution results and identify patterns "
            "of missed signals or repeated failures before evaluating strategies."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent runs to return (default 10)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_broker_account",
        "description": "Return KIS account balance, buying power, and positions (국내+해외).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "place_order",
        "description": "Place a buy or sell order via KIS. 국내(6자리 숫자 ticker)와 미국(영문 ticker)을 자동 분기.",  # noqa: E501
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "종목 코드. 국내: 6자리 숫자(005930), 미국: 영문(AAPL)",
                },
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "qty": {"type": "number", "description": "Number of shares (정수)"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "limit_price": {
                    "type": "number",
                    "description": "Limit price. 국내: KRW, 미국: USD",
                },
                "strategy_id": {
                    "type": "integer",
                    "description": "Associated strategy ID for logging",
                },
                "ai_reasoning": {
                    "type": "string",
                    "description": "AI's reason for placing this order",
                },
                "max_position": {
                    "type": "number",
                    "description": (
                        "포지션 한도 (strategy currency 단위). 설정 시 한도 초과 주문은 자동 거부."
                    ),
                },
            },
            "required": ["ticker", "side", "qty"],
        },
    },
    {
        "name": "get_strategies",
        "description": "Return saved trading strategies to check execution conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed"],
                },
            },
            "required": [],
        },
    },
    {
        "name": "evaluate_strategy",
        "description": (
            "Evaluate a strategy's entry/exit conditions using real-time price data. "
            "Returns entry_triggered, exit_triggered, and per-condition details. "
            "Always call this for each active strategy instead of using web_search to check prices manually."  # noqa: E501
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {"type": "integer", "description": "Strategy ID to evaluate"},
            },
            "required": ["strategy_id"],
        },
    },
    {
        "name": "check_dca_due",
        "description": (
            "Check if a DCA strategy is due for its next buy. "
            "Returns is_due (bool), days_since_last, and dca_frequency_days. "
            "Always call this for DCA strategies instead of computing intervals manually."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_id": {"type": "integer", "description": "Strategy ID to check"},
            },
            "required": ["strategy_id"],
        },
    },
]

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}
