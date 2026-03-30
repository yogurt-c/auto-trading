"""Portfolio domain services."""

from __future__ import annotations

from .value_objects import (
    HoldingValuation,
    Money,
    PerformanceSummary,
    PeriodPnl,
    PortfolioSnapshot,
    RealizedTradeVO,
    StrategyPnl,
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
        """Calculate portfolio valuation snapshot.

        Args:
            holdings: list of holding dicts from core/portfolio.get_all_holdings()
            current_prices: ticker → price map from core/market.get_current_prices()

        Returns:
            PortfolioSnapshot with per-holding valuations and portfolio totals.
        """
        holding_valuations: list[HoldingValuation] = []

        for h in holdings:
            ticker = h["ticker"]
            shares = float(h["shares"])
            avg_price = float(h["avg_price"])
            current_price = float(current_prices.get(ticker, avg_price))

            market_value = shares * current_price
            cost_basis = shares * avg_price
            pnl = market_value - cost_basis
            pnl_pct = round((pnl / cost_basis * 100) if cost_basis else 0.0, 2)

            holding_valuations.append(
                HoldingValuation(
                    ticker=ticker,
                    shares=shares,
                    avg_price=Money(amount=avg_price),
                    current_price=Money(amount=current_price),
                    market_value=Money(amount=market_value),
                    cost_basis=Money(amount=cost_basis),
                    pnl=Money(amount=pnl),
                    pnl_pct=pnl_pct,
                )
            )

        total_market_value = sum(hv.market_value.amount for hv in holding_valuations)
        total_cost_basis = sum(hv.cost_basis.amount for hv in holding_valuations)
        total_pnl = total_market_value - total_cost_basis
        total_pnl_pct = round((total_pnl / total_cost_basis * 100) if total_cost_basis else 0.0, 2)

        return PortfolioSnapshot(
            holdings=holding_valuations,
            total_market_value=Money(amount=total_market_value),
            total_cost_basis=Money(amount=total_cost_basis),
            total_pnl=Money(amount=total_pnl),
            total_pnl_pct=total_pnl_pct,
        )


class RealizedPnlAggregator:
    """순수 집계 서비스 — I/O 없음.

    realized_trades rows가 이미 (sell_price, avg_cost, realized_pnl)을 가지고 있으므로
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
        period_buckets: dict[str, list[RealizedTradeVO]] = {}
        for t in trades:
            key = t.executed_at.strftime("%Y-%m") if group_by == "month" else t.executed_at.strftime("%Y-%m-%d")
            period_buckets.setdefault(key, []).append(t)

        by_period = [
            PeriodPnl(
                period=period,
                realized_pnl=sum(t.realized_pnl for t in bucket),
                trade_count=len(bucket),
            )
            for period, bucket in sorted(period_buckets.items())
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
