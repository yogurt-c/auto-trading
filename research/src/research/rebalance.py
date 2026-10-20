"""앱 월 리밸런싱 주문 계획 — Android `core.RebalancePlanner`의 기준 구현.

shared/fixtures/rebalance를 이 모듈로 생성한다. 백테스트(rotation.run_rotation)와 같은 규칙에
앱 실행용 규칙 두 가지를 더한다:
- 주문 1건 금액이 계획 시점 총자산의 min_order_fraction 미만이면 생략
  (성향에서 빠진 종목 매도는 예외)
- 매수는 매도 체결 후 실제 예수금으로 계획하고, 시장가 체결 오차에 대비해
  가격에 cost_reserve를 더해 잡는다

앱은 성향의 ETF만 관리한다. 계좌의 다른 종목은 총자산 계산에도 넣지 않고 주문하지 않는다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

CASH_BUFFER = 0.005
MIN_ORDER_FRACTION = 0.01
COST_RESERVE = 0.002


@dataclass(frozen=True)
class OrderIntent:
    code: str
    side: str  # "sell" | "buy"
    qty: int


def managed_equity(
    holdings: dict[str, int], prices: dict[str, float], cash: float, managed: set[str]
) -> float:
    """관리 대상(성향 ETF + 이전 성향 ETF) 평가액 + 예수금."""
    return cash + sum(qty * prices[code] for code, qty in holdings.items() if code in managed)


def target_shares(
    weights: dict[str, float], equity: float, prices: dict[str, float], cash_buffer: float
) -> dict[str, int]:
    budget = equity * (1 - cash_buffer)
    return {
        code: math.floor(budget * w / prices[code]) for code, w in sorted(weights.items()) if w > 0
    }


def plan_sells(
    holdings: dict[str, int],
    targets: dict[str, int],
    prices: dict[str, float],
    equity: float,
    managed: set[str],
    min_order_fraction: float,
) -> list[OrderIntent]:
    """목표보다 많은 수량을 매도. 성향에서 빠진 관리 종목은 금액과 무관하게 전량 매도."""
    orders = []
    for code in sorted(holdings):
        if code not in managed:
            continue
        excess = holdings[code] - targets.get(code, 0)
        if excess <= 0:
            continue
        if code in targets and excess * prices[code] < equity * min_order_fraction:
            continue
        orders.append(OrderIntent(code, "sell", excess))
    return orders


def plan_buys(
    holdings: dict[str, int],
    targets: dict[str, int],
    prices: dict[str, float],
    cash: float,
    equity: float,
    min_order_fraction: float,
    cost_reserve: float,
) -> list[OrderIntent]:
    """목표보다 적은 수량을 매수 (종목코드 순). 예수금이 모자라면 뒤 종목부터 줄어든다."""
    orders = []
    for code in sorted(targets):
        shortfall = targets[code] - holdings.get(code, 0)
        if shortfall <= 0 or shortfall * prices[code] < equity * min_order_fraction:
            continue
        unit = prices[code] * (1 + cost_reserve)
        qty = min(shortfall, math.floor(cash / unit))
        if qty <= 0:
            continue
        orders.append(OrderIntent(code, "buy", qty))
        cash -= qty * unit
    return orders
