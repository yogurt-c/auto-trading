"""Portfolio domain services."""

from __future__ import annotations

from .value_objects import HoldingValuation, Money, PortfolioSnapshot


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
        total_pnl_pct = round(
            (total_pnl / total_cost_basis * 100) if total_cost_basis else 0.0, 2
        )

        return PortfolioSnapshot(
            holdings=holding_valuations,
            total_market_value=Money(amount=total_market_value),
            total_cost_basis=Money(amount=total_cost_basis),
            total_pnl=Money(amount=total_pnl),
            total_pnl_pct=total_pnl_pct,
        )
