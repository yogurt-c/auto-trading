"""Portfolio API — holdings, sync, transactions."""

from fastapi import APIRouter, HTTPException, Query

from infrastructure import repository as db
from infrastructure import alpaca_client
from infrastructure.market import get_current_prices
from domain.portfolio.services import PortfolioValuationService

router = APIRouter()
_valuation_service = PortfolioValuationService()


@router.get("/portfolio")
def get_portfolio():
    """전체 holdings + P&L 계산 (현재가 기준)."""
    holdings = db.get_all_holdings()
    if not holdings:
        return {"holdings": [], "summary": {}, "failed_tickers": [], "count": 0}

    tickers = [h["ticker"] for h in holdings]
    prices = get_current_prices(tickers)
    failed_tickers = [t for t in tickers if t not in prices]

    snapshot = _valuation_service.calculate(holdings, prices)

    holding_list = [
        {
            "ticker": hv.ticker,
            "shares": float(hv.shares),
            "avg_price": float(hv.avg_price.amount),
            "current_price": float(hv.current_price.amount),
            "market_value": float(hv.market_value.amount),
            "cost_basis": float(hv.cost_basis.amount),
            "pnl": float(hv.pnl.amount),
            "pnl_pct": float(hv.pnl_pct),
        }
        for hv in snapshot.holdings
    ]

    return {
        "holdings": holding_list,
        "summary": {
            "total_market_value": float(snapshot.total_market_value.amount),
            "total_cost_basis": float(snapshot.total_cost_basis.amount),
            "total_pnl": float(snapshot.total_pnl.amount),
            "total_pnl_pct": float(snapshot.total_pnl_pct),
        },
        "failed_tickers": failed_tickers,
        "count": len(holdings),
    }


@router.post("/portfolio/sync")
def sync_holdings():
    """Alpaca 전체 포지션으로 holdings 테이블 즉시 재구성."""
    try:
        positions = alpaca_client.sync_positions()
        return {"success": True, "synced_count": len(positions), "holdings": positions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "unauthorized" in err_str.lower():
            raise HTTPException(status_code=401, detail="Alpaca API 인증 실패. Settings 페이지에서 API 키를 확인해 주세요.")
        raise HTTPException(status_code=503, detail=f"Alpaca sync 실패: {err_str}")


@router.get("/portfolio/holdings")
def get_holdings():
    """DB에서 보유 종목 목록 반환 (시세 조회 없음)."""
    holdings = db.get_all_holdings()
    return {"holdings": holdings, "count": len(holdings)}


@router.get("/portfolio/transactions")
def get_transactions(limit: int = Query(50, ge=1, le=500)):
    """거래 내역 반환."""
    txns = db.get_transactions(limit=limit)
    return {"transactions": txns, "count": len(txns)}
