"""Agent tool definitions.

Each function here corresponds to a tool the agent can call.
Tool schemas (for Anthropic tool_use) are also defined here.
"""

from __future__ import annotations

import json
from typing import Any

from . import portfolio as db
from . import alpaca_client


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_portfolio() -> dict:
    """Return the full portfolio: all holdings with metadata."""
    holdings = db.get_all_holdings()
    return {"holdings": holdings, "count": len(holdings)}


def add_holding(ticker: str, shares: float, avg_price: float) -> dict:
    """Add or update a holding (uses weighted average for avg_price)."""
    result = db.upsert_holding(ticker, shares, avg_price)
    return {"success": True, "holding": result}


def remove_holding(ticker: str) -> dict:
    """Remove a holding from the portfolio."""
    ok = db.remove_holding(ticker)
    return {"success": ok, "ticker": ticker.upper()}


def get_strategies(status: str | None = None) -> dict:
    """
    Return saved trading strategies.
    status: 'active' | 'paused' | 'completed' | None (all)
    """
    strategies = db.get_strategies(status)
    return {"strategies": strategies, "count": len(strategies)}


def save_strategy(
    name: str,
    strategy_type: str,
    description: str,
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
    return {"success": True, "strategy": result}


def update_strategy_status(strategy_id: int, status: str) -> dict:
    """Update strategy status: 'active' | 'paused' | 'completed'."""
    result = db.update_strategy_status(strategy_id, status)
    if result:
        return {"success": True, "strategy": result}
    return {"success": False, "error": f"Strategy {strategy_id} not found"}


def get_alpaca_account() -> dict:
    """Return Alpaca paper trading account info and open positions."""
    try:
        account = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
        return {"account": account, "positions": positions}
    except Exception as e:
        return {"error": str(e)}


def get_scheduler_runs(limit: int = 10) -> dict:
    """최근 스케줄러 실행 이력 반환. Trade Executor가 과거 실행 결과를 참고해 판단에 활용."""
    runs = db.get_scheduler_runs(limit=limit)
    return {"runs": runs, "count": len(runs)}


def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
    strategy_id: int | None = None,
    ai_reasoning: str | None = None,
) -> dict:
    """
    Place a buy or sell order on Alpaca paper trading and log it.
    side: 'buy' | 'sell'
    order_type: 'market' | 'limit'
    """
    try:
        order = alpaca_client.place_order(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            limit_price=limit_price,
        )
        log = db.add_trade_log(
            ticker=ticker,
            side=side,
            qty=qty,
            order_type=order_type,
            status=order["status"],
            strategy_id=strategy_id,
            limit_price=limit_price,
            alpaca_id=order["alpaca_id"],
            ai_reasoning=ai_reasoning,
        )
        return {"success": True, "order": order, "log_id": log["id"]}
    except Exception as e:
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
    "add_holding": add_holding,
    "remove_holding": remove_holding,
    "get_strategies": get_strategies,
    "save_strategy": save_strategy,
    "update_strategy_status": update_strategy_status,
    "get_alpaca_account": get_alpaca_account,
    "place_order": place_order,
    "get_scheduler_runs": get_scheduler_runs,
}


def dispatch_tool(name: str, inputs: dict) -> Any:
    """Execute a tool by name with the given inputs dict."""
    fn = TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    return fn(**inputs)


# ---------------------------------------------------------------------------
# Anthropic tool schemas
# ---------------------------------------------------------------------------

PORTFOLIO_TOOLS = [
    {
        "name": "get_portfolio",
        "description": "Return all holdings in the portfolio with ticker, shares, avg_price, created_at.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_holding",
        "description": "Add a new holding or increase position using weighted average for avg_price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock/ETF ticker symbol (e.g. AAPL)"},
                "shares": {"type": "number", "description": "Number of shares to add"},
                "avg_price": {"type": "number", "description": "Purchase price per share"},
            },
            "required": ["ticker", "shares", "avg_price"],
        },
    },
    {
        "name": "remove_holding",
        "description": "Remove a holding from the portfolio entirely.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock/ETF ticker symbol to remove"},
            },
            "required": ["ticker"],
        },
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
                "description": {"type": "string", "description": "Summary of the strategy agreed with user"},
                "ticker": {"type": "string", "description": "Target ticker (null = whole portfolio)"},
                "ai_rationale": {"type": "string", "description": "AI's reasoning for this strategy"},
                "entry_price_drop_pct": {"type": "number", "description": "Buy trigger: % drop from current price (negative, e.g. -5.0)"},
                "entry_rsi_below": {"type": "number", "description": "Buy trigger: RSI threshold (e.g. 30)"},
                "take_profit_pct": {"type": "number", "description": "Sell trigger: target profit % (e.g. 20.0)"},
                "stop_loss_pct": {"type": "number", "description": "Sell trigger: stop loss % (e.g. -10.0)"},
                "sell_ratio": {"type": "number", "description": "Fraction of position to sell (0.5 = half)"},
                "dca_amount_usd": {"type": "number", "description": "USD amount per DCA purchase"},
                "dca_frequency_days": {"type": "integer", "description": "DCA interval in days"},
                "max_position_usd": {"type": "number", "description": "Maximum total investment in USD"},
                "strategy_id": {"type": "integer", "description": "Existing strategy ID to update (omit to create new)"},
            },
            "required": ["name", "strategy_type", "description"],
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
        "description": "Return Alpaca paper trading account balance, buying power, and open positions.",
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
                "limit_price": {"type": "number", "description": "Limit price (only for limit orders)"},
                "strategy_id": {"type": "integer", "description": "Associated strategy ID for logging"},
                "ai_reasoning": {"type": "string", "description": "AI's reason for placing this order"},
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
]

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
}
