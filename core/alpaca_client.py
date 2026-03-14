"""Alpaca Paper Trading API wrapper."""

from __future__ import annotations

from .config import get_settings

_client = None


def _get_client():
    global _client
    if _client is None:
        from alpaca.trading.client import TradingClient

        s = get_settings()
        if not s.alpaca_api_key or not s.alpaca_secret_key:
            raise ValueError("Alpaca API 키가 설정되지 않았습니다. Settings 페이지에서 입력해 주세요.")
        _client = TradingClient(s.alpaca_api_key, s.alpaca_secret_key, paper=s.alpaca_paper)
    return _client


def reset_client() -> None:
    """Force reconnect on next call (e.g. after settings change)."""
    global _client
    _client = None


def get_account() -> dict:
    client = _get_client()
    acct = client.get_account()
    return {
        "cash": float(acct.cash),
        "portfolio_value": float(acct.portfolio_value),
        "buying_power": float(acct.buying_power),
        "currency": acct.currency,
        "status": acct.status,
    }


def get_positions() -> list[dict]:
    client = _get_client()
    return [
        {
            "ticker": p.symbol,
            "qty": float(p.qty),
            "avg_entry_price": float(p.avg_entry_price),
            "current_price": float(p.current_price),
            "market_value": float(p.market_value),
            "unrealized_pl": float(p.unrealized_pl),
            "unrealized_plpc": float(p.unrealized_plpc),
        }
        for p in client.get_all_positions()
    ]


def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
) -> dict:
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import LimitOrderRequest, MarketOrderRequest

    client = _get_client()
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    if order_type == "limit" and limit_price:
        req = LimitOrderRequest(
            symbol=ticker.upper(), qty=qty, side=order_side,
            time_in_force=TimeInForce.DAY, limit_price=limit_price,
        )
    else:
        req = MarketOrderRequest(
            symbol=ticker.upper(), qty=qty, side=order_side,
            time_in_force=TimeInForce.DAY,
        )

    order = client.submit_order(req)
    return {
        "alpaca_id": str(order.id),
        "ticker": order.symbol,
        "side": order.side.value,
        "qty": float(order.qty),
        "order_type": order.type.value,
        "status": order.status.value,
        "limit_price": float(order.limit_price) if order.limit_price else None,
    }
