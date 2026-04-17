"""Portfolio domain services."""

from __future__ import annotations

from .value_objects import (
    HoldingValuation,
    MarketSummary,
    Money,
    PerformanceSummary,
    PeriodPnl,
    PortfolioSnapshot,
    RealizedTradeVO,
    StrategyPnl,
)


def _make_market_summary(
    hvs: list[HoldingValuation],
    market: str,
    currency: str,
) -> MarketSummary:
    mv = sum(hv.market_value.amount for hv in hvs)
    cb = sum(hv.cost_basis.amount for hv in hvs)
    pnl = mv - cb
    return MarketSummary(
        market=market,
        currency=currency,
        total_market_value=Money(amount=mv, currency=currency),
        total_cost_basis=Money(amount=cb, currency=currency),
        total_pnl=Money(amount=pnl, currency=currency),
        total_pnl_pct=round(pnl / cb * 100 if cb else 0.0, 2),
        holding_count=len(hvs),
    )


class PortfolioValuationService:
    """Pure calculation service — no I/O.

    Caller is responsible for fetching holdings and current prices,
    then injecting them here.
    """

    def calculate(
        self,
        holdings: list[dict],
        current_prices: dict[str, float],
    ) -> PortfolioSnapshot:
        """Calculate portfolio valuation snapshot, split by KR/US market.

        Args:
            holdings: list of holding dicts from core/portfolio.get_all_holdings()
            current_prices: ticker → price map from core/market.get_current_prices()

        Returns:
            PortfolioSnapshot with per-holding valuations and separate KR/US summaries.
        """
        holding_valuations: list[HoldingValuation] = []

        for h in holdings:
            ticker = h["ticker"]
            shares = float(h["shares"])
            avg_price = float(h["avg_price"])
            current_price = float(current_prices.get(ticker, avg_price))
            market = h.get("market", "US")
            currency = h.get("currency", "USD")

            market_value = shares * current_price
            cost_basis = shares * avg_price
            pnl = market_value - cost_basis
            pnl_pct = round((pnl / cost_basis * 100) if cost_basis else 0.0, 2)

            holding_valuations.append(
                HoldingValuation(
                    ticker=ticker,
                    shares=shares,
                    avg_price=Money(amount=avg_price, currency=currency),
                    current_price=Money(amount=current_price, currency=currency),
                    market_value=Money(amount=market_value, currency=currency),
                    cost_basis=Money(amount=cost_basis, currency=currency),
                    pnl=Money(amount=pnl, currency=currency),
                    pnl_pct=pnl_pct,
                    market=market,
                    currency=currency,
                )
            )

        kr_hvs = [hv for hv in holding_valuations if hv.market == "KR"]
        us_hvs = [hv for hv in holding_valuations if hv.market != "KR"]

        return PortfolioSnapshot(
            holdings=holding_valuations,
            kr=_make_market_summary(kr_hvs, "KR", "KRW") if kr_hvs else None,
            us=_make_market_summary(us_hvs, "US", "USD") if us_hvs else None,
        )


class RealizedPnlAggregator:
    """순수 집계 서비스 — I/O 없음.

    realized_trades rows가 이미 (sell_price, avg_cost, realized_pnl, currency)을 가지고 있으므로
    재계산 불필요. by_period / by_strategy 집계만 수행.
    """

    def aggregate(
        self,
        realized_trade_dicts: list[dict],
        strategy_names: dict[int, str],
        start_date: str,
        end_date: str,
        group_by: str = "day",
    ) -> PerformanceSummary:
        trades = [
            RealizedTradeVO(
                **{k: v for k, v in rt.items() if k != "strategy_name"},
                strategy_name=strategy_names.get(rt["strategy_id"])
                if rt.get("strategy_id") is not None
                else None,
            )
            for rt in realized_trade_dicts
        ]

        win_count = sum(1 for t in trades if t.realized_pnl > 0)
        total_trade_count = len(trades)
        total_realized_pnl = sum(t.realized_pnl for t in trades)
        win_rate = round((win_count / total_trade_count * 100) if total_trade_count else 0.0, 2)

        # --- by_period ---
        period_buckets: dict[tuple[str, str], list[RealizedTradeVO]] = {}
        for t in trades:
            period_str = (
                t.executed_at.strftime("%Y-%m")
                if group_by == "month"
                else t.executed_at.strftime("%Y-%m-%d")
            )
            period_buckets.setdefault((period_str, t.currency), []).append(t)

        by_period = [
            PeriodPnl(
                period=period,
                currency=currency,
                realized_pnl=sum(t.realized_pnl for t in bucket),
                trade_count=len(bucket),
            )
            for (period, currency), bucket in sorted(period_buckets.items())
        ]

        # --- by_strategy ---
        strategy_buckets: dict[int | None, list[RealizedTradeVO]] = {}
        for t in trades:
            strategy_buckets.setdefault(t.strategy_id, []).append(t)

        by_strategy = []
        for sid, bucket in strategy_buckets.items():
            s_win = sum(1 for t in bucket if t.realized_pnl > 0)
            s_count = len(bucket)
            name = strategy_names.get(sid, "Manual") if sid is not None else "Manual"
            by_strategy.append(
                StrategyPnl(
                    strategy_id=sid,
                    strategy_name=name,
                    realized_pnl=sum(t.realized_pnl for t in bucket),
                    trade_count=s_count,
                    win_count=s_win,
                    win_rate=round((s_win / s_count * 100) if s_count else 0.0, 2),
                )
            )
        by_strategy.sort(key=lambda x: x.realized_pnl, reverse=True)

        return PerformanceSummary(
            period_start=start_date,
            period_end=end_date,
            total_realized_pnl=total_realized_pnl,
            total_trade_count=total_trade_count,
            win_count=win_count,
            win_rate=win_rate,
            trades=trades,
            by_period=by_period,
            by_strategy=by_strategy,
        )
