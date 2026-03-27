"""Agent tool definitions.

Each function here corresponds to a tool the agent can call.
Tool schemas (for Anthropic tool_use) are also defined here.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.domain.portfolio.services import PortfolioValuationService, RealizedPnlAggregator
from app.domain.trading_strategy.services import (
    DcaScheduleChecker,
    StrategyEvaluator,
    StrategyValidator,
)
from app.domain.trading_strategy.value_objects import MarketData
from app.infrastructure import alpaca_client
from app.infrastructure import market as market_data
from app.infrastructure import repository as db

_strategy_validator = StrategyValidator()
_strategy_evaluator = StrategyEvaluator()
_dca_checker = DcaScheduleChecker()
_valuation_service = PortfolioValuationService()
_pnl_aggregator = RealizedPnlAggregator()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_portfolio() -> dict:
    """Return the full portfolio: all holdings with metadata."""
    holdings = db.get_all_holdings()
    return {"holdings": holdings, "count": len(holdings)}


def sync_holdings() -> dict:
    """Alpaca 전체 포지션으로 holdings 테이블을 즉시 재구성."""
    try:
        positions = alpaca_client.sync_positions()
        logger.info(f"holdings synced from Alpaca: {len(positions)} positions")
        return {"success": True, "synced_count": len(positions), "holdings": positions}
    except Exception as e:
        logger.warning(f"Alpaca sync failed, holdings unchanged: {e}")
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
    dca_amount_usd: float | None,
    dca_frequency_days: int | None,
    max_position_usd: float | None,
) -> list[str]:
    """전략 파라미터 충돌·범위 검증. 경고 메시지 목록 반환."""
    domain_warnings = _strategy_validator.validate(
        strategy_type=strategy_type,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount_usd=dca_amount_usd,
        dca_frequency_days=dca_frequency_days,
        max_position_usd=max_position_usd,
    )
    return [w.message for w in domain_warnings]


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
    """Save or update a trading strategy in the database."""
    warnings = _validate_strategy_params(
        strategy_type=strategy_type,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount_usd=dca_amount_usd,
        dca_frequency_days=dca_frequency_days,
        max_position_usd=max_position_usd,
    )
    for w in warnings:
        logger.warning(w)
    result = db.save_strategy(
        name=name,
        strategy_type=strategy_type,
        description=description,
        ticker=ticker,
        ai_rationale=ai_rationale,
        entry_price_drop_pct=entry_price_drop_pct,
        entry_rsi_below=entry_rsi_below,
        take_profit_pct=take_profit_pct,
        stop_loss_pct=stop_loss_pct,
        sell_ratio=sell_ratio,
        dca_amount_usd=dca_amount_usd,
        dca_frequency_days=dca_frequency_days,
        max_position_usd=max_position_usd,
        strategy_id=strategy_id,
    )
    return {"success": True, "strategy": result, "warnings": warnings}


def update_strategy_status(strategy_id: int, status: str) -> dict:
    """Update strategy status: 'active' | 'paused' | 'completed'."""
    result = db.update_strategy_status(strategy_id, status)
    if result:
        return {"success": True, "strategy": result}
    return {"success": False, "error": f"Strategy {strategy_id} not found"}


def evaluate_strategy(strategy_id: int) -> dict:
    """
    전략의 진입/청산 조건을 현재가 기준으로 평가.
    - entry_price_drop_pct: 30일 고점 대비 하락률
    - entry_rsi_below: 14일 RSI 계산
    - take_profit_pct / stop_loss_pct: 보유 평균단가 대비 수익률
    """
    import math

    import yfinance as yf

    strategies = db.get_strategies()
    strategy = next((s for s in strategies if s["id"] == strategy_id), None)
    if strategy is None:
        return {"error": f"Strategy {strategy_id} not found"}

    ticker = strategy.get("ticker")
    if not ticker:
        return {"error": "Strategy has no ticker set"}

    try:
        data = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
    except Exception as e:
        return {"error": f"Failed to fetch price data for {ticker}: {e}"}
    if data.empty:
        return {"error": f"Could not fetch price data for {ticker}"}

    # I/O: current price and 30-day high
    current_price = float(data["Close"].squeeze().iloc[-1])
    high_30d = float(data["High"].squeeze().tail(30).max())

    # I/O: RSI calculation (pandas preprocessing stays here)
    closes = data["Close"].squeeze()
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi_series = 100 - 100 / (1 + rs)
    rsi = float(rsi_series.iloc[-1])
    if math.isnan(rsi):
        rsi = 50.0  # gain=0, loss=0 (가격 변동 없음) → 중립값

    # I/O: current holding from DB
    holdings = db.get_all_holdings()
    current_holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)

    # Assemble MarketData and delegate pure evaluation to domain service
    mkt = MarketData(ticker=ticker, current_price=current_price, high_30d=high_30d, rsi_14=rsi)
    result = _strategy_evaluator.evaluate(strategy, mkt, current_holding)

    logger.debug(
        f"evaluate_strategy id={strategy_id}: "
        f"entry={result.entry_triggered}, exit={result.exit_triggered}"
    )
    return result.model_dump()


def get_alpaca_account() -> dict:
    """Return Alpaca paper trading account info and open positions."""
    try:
        account = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
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
    strategies = db.get_strategies()
    strategy = next((s for s in strategies if s["id"] == strategy_id), None)
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


def _sync_from_alpaca() -> str:
    """주문 완료 후 Alpaca 전체 포지션으로 holdings를 재구성."""
    try:
        positions = alpaca_client.sync_positions()
        logger.info(f"holdings synced from Alpaca: {len(positions)} positions")
        return f"synced {len(positions)} positions from Alpaca"
    except Exception as e:
        logger.warning(f"Alpaca sync failed, holdings unchanged: {e}")
        return f"sync failed: {e}"


def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
    strategy_id: int | None = None,
    ai_reasoning: str | None = None,
    max_position_usd: float | None = None,
) -> dict:
    """
    Place a buy or sell order on Alpaca paper trading and log it.
    side: 'buy' | 'sell'
    order_type: 'market' | 'limit'
    max_position_usd: if set, rejects buy orders that would exceed this position size
    """
    # max_position_usd 한도 검증 (매수 시에만)
    if max_position_usd and side.lower() == "buy":
        check_price = limit_price
        if check_price is None:
            prices = market_data.get_current_prices([ticker.upper()])
            check_price = prices.get(ticker.upper())

        if check_price:
            holdings = db.get_all_holdings()
            holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)
            current_value = (holding["shares"] * check_price) if holding else 0.0
            order_value = qty * check_price
            projected_value = current_value + order_value

            if projected_value > max_position_usd:
                detail = (
                    f"현재 {current_value:.2f} USD + 신규 {order_value:.2f} USD "
                    f"= {projected_value:.2f} USD (한도 {max_position_usd:.2f} USD)"
                )
                logger.warning(f"order rejected — max_position_usd exceeded: {detail}")
                return {
                    "success": False,
                    "error": f"max_position_usd 한도 초과: {detail}",
                }

    # 매도 시 avg_cost 미리 조회 (Alpaca sync 이전에 수행해야 정확한 값 보장)
    avg_cost: float | None = None
    if side.lower() == "sell":
        holdings = db.get_all_holdings()
        holding = next((h for h in holdings if h["ticker"] == ticker.upper()), None)
        avg_cost = holding["avg_price"] if holding else None

    try:
        order = alpaca_client.place_order(
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
            alpaca_id=order["alpaca_id"],
            ai_reasoning=ai_reasoning,
        )

        # 매도 체결 시 실현 손익 스냅샷 저장
        if (
            side.lower() == "sell"
            and order["status"] == "filled"
            and avg_cost is not None
            and filled_price is not None
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
                strategy_id=strategy_id,
            )
            logger.info(
                f"realized_trade saved: {ticker} qty={qty} "
                f"sell={filled_price} cost={avg_cost} pnl={pnl:.2f}"
            )

        # holdings DB 동기화
        holdings_synced = _sync_from_alpaca()
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
            ai_reasoning=f"Error: {e}",
        )
        return {"success": False, "error": str(e)}


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
    "get_alpaca_account": get_alpaca_account,
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
        "description": "Return all holdings in the portfolio with ticker, shares, avg_price, created_at.",  # noqa: E501
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "sync_holdings",
        "description": (
            "Sync holdings table from Alpaca positions (single source of truth). "
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
                    "description": "Target ticker (null = whole portfolio)",
                },
                "ai_rationale": {
                    "type": "string",
                    "description": "AI's reasoning for this strategy",
                },
                "entry_price_drop_pct": {
                    "type": "number",
                    "description": "Buy trigger: % drop from current price (negative, e.g. -5.0)",
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
                "dca_amount_usd": {"type": "number", "description": "USD amount per DCA purchase"},
                "dca_frequency_days": {"type": "integer", "description": "DCA interval in days"},
                "max_position_usd": {
                    "type": "number",
                    "description": "Maximum total investment in USD",
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
        "name": "get_alpaca_account",
        "description": "Return Alpaca paper trading account balance, buying power, and open positions.",  # noqa: E501
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "place_order",
        "description": "Place a buy or sell order on Alpaca paper trading.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock/ETF symbol"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "qty": {"type": "number", "description": "Number of shares"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "limit_price": {
                    "type": "number",
                    "description": "Limit price (only for limit orders)",
                },
                "strategy_id": {
                    "type": "integer",
                    "description": "Associated strategy ID for logging",
                },
                "ai_reasoning": {
                    "type": "string",
                    "description": "AI's reason for placing this order",
                },
                "max_position_usd": {
                    "type": "number",
                    "description": (
                        "Position size cap in USD from the strategy. "
                        "If set, the order is rejected before submission if it would exceed this limit."  # noqa: E501
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
