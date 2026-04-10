"""Unit tests for RealizedPnlAggregator."""

import pytest

from app.domain.portfolio.services import RealizedPnlAggregator


@pytest.fixture
def aggregator():
    return RealizedPnlAggregator()


def _make_rt(
    id: int = 1,
    ticker: str = "AAPL",
    qty: float = 10.0,
    sell_price: float = 150.0,
    avg_cost: float = 100.0,
    strategy_id: int | None = None,
    executed_at: str = "2026-03-15T14:30:00",
    currency: str = "USD",
) -> dict:
    pnl = (sell_price - avg_cost) * qty
    pnl_pct = round((pnl / (avg_cost * qty) * 100) if avg_cost else 0.0, 2)
    return {
        "id": id,
        "trade_log_id": id,
        "ticker": ticker,
        "qty": qty,
        "sell_price": sell_price,
        "avg_cost": avg_cost,
        "realized_pnl": pnl,
        "realized_pnl_pct": pnl_pct,
        "currency": currency,
        "strategy_id": strategy_id,
        "executed_at": executed_at,
    }


# ---------------------------------------------------------------------------
# Basic cases
# ---------------------------------------------------------------------------


def test_single_profit(aggregator):
    """단일 매도 양수 수익 집계."""
    rt = _make_rt(sell_price=150.0, avg_cost=100.0, qty=10.0)
    summary = aggregator.aggregate([rt], {}, "2026-03-01", "2026-03-31")

    assert summary.total_realized_pnl == pytest.approx(500.0)
    assert summary.total_trade_count == 1
    assert summary.win_count == 1
    assert summary.win_rate == pytest.approx(100.0)


def test_single_loss(aggregator):
    """단일 매도 손실 집계."""
    rt = _make_rt(sell_price=80.0, avg_cost=100.0, qty=10.0)
    summary = aggregator.aggregate([rt], {}, "2026-03-01", "2026-03-31")

    assert summary.total_realized_pnl == pytest.approx(-200.0)
    assert summary.total_trade_count == 1
    assert summary.win_count == 0
    assert summary.win_rate == pytest.approx(0.0)


def test_empty_input(aggregator):
    """빈 입력 처리."""
    summary = aggregator.aggregate([], {}, "2026-03-01", "2026-03-31")

    assert summary.total_realized_pnl == pytest.approx(0.0)
    assert summary.total_trade_count == 0
    assert summary.win_count == 0
    assert summary.win_rate == pytest.approx(0.0)
    assert summary.trades == []
    assert summary.by_period == []
    assert summary.by_strategy == []


# ---------------------------------------------------------------------------
# Period grouping
# ---------------------------------------------------------------------------


def test_period_grouping_by_day(aggregator):
    """일별 집계: 두 날짜에 각 1건."""
    trades = [
        _make_rt(
            id=1, sell_price=120.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-10T10:00:00"
        ),
        _make_rt(id=2, sell_price=80.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-15T11:00:00"),
    ]
    summary = aggregator.aggregate(trades, {}, "2026-03-01", "2026-03-31", group_by="day")

    assert len(summary.by_period) == 2
    periods = {p.period: p for p in summary.by_period}
    assert "2026-03-10" in periods
    assert "2026-03-15" in periods
    assert periods["2026-03-10"].realized_pnl == pytest.approx(100.0)
    assert periods["2026-03-15"].realized_pnl == pytest.approx(-100.0)
    assert periods["2026-03-10"].trade_count == 1
    assert periods["2026-03-15"].trade_count == 1


def test_period_grouping_by_month(aggregator):
    """월별 집계: 같은 월 2건 → 하나의 버킷."""
    trades = [
        _make_rt(
            id=1, sell_price=120.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-05T10:00:00"
        ),
        _make_rt(
            id=2, sell_price=130.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-20T10:00:00"
        ),
    ]
    summary = aggregator.aggregate(trades, {}, "2026-03-01", "2026-03-31", group_by="month")

    assert len(summary.by_period) == 1
    bucket = summary.by_period[0]
    assert bucket.period == "2026-03"
    assert bucket.trade_count == 2
    assert bucket.realized_pnl == pytest.approx(100.0 + 150.0)


def test_period_grouping_across_months(aggregator):
    """두 다른 월 → 두 개의 월별 버킷."""
    trades = [
        _make_rt(
            id=1, sell_price=110.0, avg_cost=100.0, qty=10.0, executed_at="2026-02-20T10:00:00"
        ),
        _make_rt(
            id=2, sell_price=90.0, avg_cost=100.0, qty=10.0, executed_at="2026-03-10T10:00:00"
        ),
    ]
    summary = aggregator.aggregate(trades, {}, "2026-02-01", "2026-03-31", group_by="month")

    assert len(summary.by_period) == 2
    periods = {p.period: p for p in summary.by_period}
    assert "2026-02" in periods
    assert "2026-03" in periods


# ---------------------------------------------------------------------------
# Strategy grouping
# ---------------------------------------------------------------------------


def test_strategy_grouping_with_win_rate(aggregator):
    """전략별 집계 + 승률 계산."""
    strategy_names = {1: "AAPL Take Profit", 2: "MSFT Stop Loss"}
    trades = [
        _make_rt(
            id=1,
            sell_price=120.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=1,
            executed_at="2026-03-10T10:00:00",
        ),
        _make_rt(
            id=2,
            sell_price=110.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=1,
            executed_at="2026-03-12T10:00:00",
        ),
        _make_rt(
            id=3,
            sell_price=80.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=1,
            executed_at="2026-03-14T10:00:00",
        ),
        _make_rt(
            id=4,
            sell_price=90.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=2,
            executed_at="2026-03-16T10:00:00",
        ),
    ]
    summary = aggregator.aggregate(trades, strategy_names, "2026-03-01", "2026-03-31")

    assert len(summary.by_strategy) == 2
    s_map = {s.strategy_id: s for s in summary.by_strategy}

    s1 = s_map[1]
    assert s1.strategy_name == "AAPL Take Profit"
    assert s1.trade_count == 3
    assert s1.win_count == 2
    assert s1.win_rate == pytest.approx(66.67, abs=0.01)
    assert s1.realized_pnl == pytest.approx(100.0 + 50.0 - 100.0)

    s2 = s_map[2]
    assert s2.strategy_name == "MSFT Stop Loss"
    assert s2.trade_count == 1
    assert s2.win_count == 0
    assert s2.win_rate == pytest.approx(0.0)


def test_strategy_grouping_manual_trades(aggregator):
    """strategy_id=None (수동 거래) → 'Manual' 전략으로 집계."""
    trades = [
        _make_rt(id=1, sell_price=120.0, avg_cost=100.0, qty=5.0, strategy_id=None),
    ]
    summary = aggregator.aggregate(trades, {}, "2026-03-01", "2026-03-31")

    assert len(summary.by_strategy) == 1
    s = summary.by_strategy[0]
    assert s.strategy_id is None
    assert s.strategy_name == "Manual"


def test_overall_win_rate(aggregator):
    """전체 승률 계산."""
    trades = [
        _make_rt(
            id=1, sell_price=120.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-10T10:00:00"
        ),
        _make_rt(
            id=2, sell_price=120.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-11T10:00:00"
        ),
        _make_rt(id=3, sell_price=80.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-12T10:00:00"),
        _make_rt(id=4, sell_price=80.0, avg_cost=100.0, qty=5.0, executed_at="2026-03-13T10:00:00"),
    ]
    summary = aggregator.aggregate(trades, {}, "2026-03-01", "2026-03-31")

    assert summary.win_count == 2
    assert summary.total_trade_count == 4
    assert summary.win_rate == pytest.approx(50.0)


def test_strategy_sorted_by_pnl_desc(aggregator):
    """by_strategy는 realized_pnl 내림차순 정렬."""
    strategy_names = {1: "S1", 2: "S2"}
    trades = [
        _make_rt(
            id=1,
            sell_price=80.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=1,
            executed_at="2026-03-10T10:00:00",
        ),
        _make_rt(
            id=2,
            sell_price=120.0,
            avg_cost=100.0,
            qty=5.0,
            strategy_id=2,
            executed_at="2026-03-11T10:00:00",
        ),
    ]
    summary = aggregator.aggregate(trades, strategy_names, "2026-03-01", "2026-03-31")

    # S2 (pnl=100) > S1 (pnl=-100) 순서
    assert summary.by_strategy[0].strategy_id == 2
    assert summary.by_strategy[1].strategy_id == 1


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


def test_currency_preserved_usd(aggregator):
    """USD currency가 RealizedTradeVO에 유지되는지 확인."""
    rt = _make_rt(currency="USD")
    summary = aggregator.aggregate([rt], {}, "2026-01-01", "2026-12-31")
    assert summary.trades[0].currency == "USD"


def test_currency_preserved_krw(aggregator):
    """KRW currency가 RealizedTradeVO에 유지되는지 확인."""
    rt = _make_rt(ticker="005930", currency="KRW")
    summary = aggregator.aggregate([rt], {}, "2026-01-01", "2026-12-31")
    assert summary.trades[0].currency == "KRW"
