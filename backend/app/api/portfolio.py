"""Portfolio API — holdings, sync, transactions."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user
from app.application.tools import get_performance as _get_performance
from app.domain.portfolio.services import PortfolioValuationService
from app.infrastructure import kis_client
from app.infrastructure import repository as db
from app.infrastructure.market import get_current_prices

router = APIRouter(dependencies=[Depends(get_current_user)])
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
    """KIS 전체 포지션으로 holdings 테이블 즉시 재구성."""
    try:
        positions = kis_client.sync_positions()
        return {"success": True, "synced_count": len(positions), "holdings": positions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "인증" in err_str or "token" in err_str.lower() or "unauthorized" in err_str.lower():
            raise HTTPException(
                status_code=401,
                detail="KIS API 인증 실패. Settings 페이지에서 API 키를 확인해 주세요.",
            )
        raise HTTPException(status_code=503, detail=f"KIS sync 실패: {err_str}")


@router.get("/portfolio/holdings")
def get_holdings():
    """DB에서 보유 종목 목록 반환 (시세 조회 없음)."""
    holdings = db.get_all_holdings()
    return {"holdings": holdings, "count": len(holdings)}


@router.get("/portfolio/transactions")
def get_transactions(limit: int = Query(50, ge=1, le=500)):
    """KIS 체결 주문 이력 반환."""
    try:
        txns = kis_client.get_filled_orders(limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"KIS 주문 이력 조회 실패: {e!s}")
    return {"transactions": txns, "count": len(txns)}


@router.get("/portfolio/performance")
def get_performance(
    start_date: str = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="시작일 (YYYY-MM-DD). 기본값: 오늘 기준 -30일",
    ),
    end_date: str = Query(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="종료일 (YYYY-MM-DD). 기본값: 오늘",
    ),
    group_by: str = Query(
        default="day",
        pattern=r"^(day|month)$",
        description="기간 집계 단위: 'day' | 'month'",
    ),
):
    """기간별 실현 손익 집계 반환."""
    today = date.today().isoformat()
    if not end_date:
        end_date = today
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")
    return _get_performance(start_date, end_date, group_by)
