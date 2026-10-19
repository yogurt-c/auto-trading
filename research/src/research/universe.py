"""시점별(point-in-time) 유니버스 — 각 리밸런싱 날짜에 알 수 있던 정보만 쓴다."""

from __future__ import annotations

import pandas as pd


def quarter_end_dates(trading_days: pd.DatetimeIndex) -> list[pd.Timestamp]:
    """분기(3·6·9·12월) 마지막 거래일 목록."""
    days = pd.Series(trading_days, index=trading_days)
    quarter_ends = days.groupby(days.index.to_period("Q")).max()
    return list(quarter_ends)


def build_universe(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """리밸런싱 날짜별 시총 상위 N 종목.

    Returns:
        columns [rebalance_date, code, rank] — rebalance_date 종가 기준, 다음 거래일부터 적용
    """
    exclude = cfg.get("exclude", {})
    min_bars = cfg["min_history_bars"]
    top_n = cfg["top_n_by_market_cap"]

    traded = panel[panel["close"].notna()].copy()
    traded["bars"] = traded.groupby("code").cumcount() + 1

    eligible = traded["bars"] >= min_bars
    if exclude.get("preferred_shares"):
        eligible &= traded["code"].str[-1] == "0"
    for word in exclude.get("name_contains", []):
        eligible &= ~traded["name"].str.contains(word, regex=False, na=False)
    candidates = traded[eligible]

    rebalance_days = set(quarter_end_dates(pd.DatetimeIndex(sorted(panel["date"].unique()))))
    snapshot = candidates[candidates["date"].isin(rebalance_days)]
    ranked = snapshot.sort_values(["date", "market_cap"], ascending=[True, False])
    ranked["rank"] = ranked.groupby("date").cumcount() + 1
    top = ranked[ranked["rank"] <= top_n]
    return top.rename(columns={"date": "rebalance_date"})[["rebalance_date", "code", "rank"]]


def members_on(universe: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """day에 적용되는 유니버스 (day보다 이전의 가장 최근 리밸런싱). 없으면 빈 DataFrame."""
    past = universe[universe["rebalance_date"] < day]
    if past.empty:
        return past
    return past[past["rebalance_date"] == past["rebalance_date"].max()]
