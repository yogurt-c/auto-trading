"""기준 전략 B1(KODEX 200 보유), B2(KODEX 200 정기 매수).

B3(유니버스 동일비중)는 종목 단위 체결·분할·배당이 필요해 engine.EqualWeightSpec으로 돌린다.
"""

from __future__ import annotations

import pandas as pd

from research.costs import CostModel


def buy_and_hold(etf: pd.DataFrame, capital: float, costs: CostModel) -> pd.Series:
    """첫 거래일 시가에 전액 매수 후 보유. etf: open/close (분배금 재투자 수정주가)."""
    price = costs.buy_price(float(etf["open"].iloc[0]))
    shares = int(capital // (price * (1 + costs.commission_rate)))
    cash = capital - costs.buy_cash_out(shares, price)
    return (cash + shares * etf["close"]).rename("B1_buy_and_hold")


def monthly_dca(etf: pd.DataFrame, capital: float, costs: CostModel) -> tuple[pd.Series, pd.Series]:
    """매월 첫 거래일 시가에 capital/개월수씩 매수.

    Returns:
        (일별 평가액, 월별 투입액) — 투입액은 금액가중수익률 계산용
    """
    days = etf.index
    month_starts = days[~days.to_period("M").duplicated()]
    budget = capital / len(month_starts)
    cash, shares = capital, 0
    flows: dict[pd.Timestamp, float] = {}
    equity: dict[pd.Timestamp, float] = {}
    for day in days:
        if day in month_starts:
            price = costs.buy_price(float(etf.at[day, "open"]))
            qty = int(min(budget, cash) // (price * (1 + costs.commission_rate)))
            spent = costs.buy_cash_out(qty, price)
            cash -= spent
            shares += qty
            flows[day] = budget
        equity[day] = cash + shares * float(etf.at[day, "close"])
    return pd.Series(equity, name="B2_monthly_dca"), pd.Series(flows)
