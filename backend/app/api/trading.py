"""Trading API — KIS account, orders, logs."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.application.tools import place_order as _place_order
from app.infrastructure import kis_client
from app.infrastructure import repository as db

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/trading/account")
def get_account():
    """KIS 계좌 정보 및 보유 포지션 반환."""
    try:
        account = kis_client.get_account()
        positions = kis_client.get_positions()
        return {"account": account, "positions": positions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "인증" in err_str or "token" in err_str.lower() or "unauthorized" in err_str.lower():
            raise HTTPException(
                status_code=401,
                detail="KIS API 인증 실패. Settings 페이지에서 API 키와 계좌번호를 확인해 주세요.",
            )
        raise HTTPException(status_code=503, detail=f"KIS API 연결 실패: {err_str}")


class OrderRequest(BaseModel):
    ticker: str
    side: Literal["buy", "sell"]
    qty: float
    order_type: Literal["market", "limit"] = "market"
    limit_price: float | None = None
    strategy_id: int | None = None
    ai_reasoning: str | None = None
    max_position: float | None = None


@router.post("/trading/orders")
def place_order(req: OrderRequest):
    """KIS 주문 실행 (국내/해외 자동 분기)."""
    return _place_order(**req.model_dump())


@router.get("/trading/logs")
def get_trade_logs(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """매매 로그 반환 (페이징 지원)."""
    logs = db.get_trade_logs(limit=limit, offset=offset)
    total = db.count_trade_logs()
    return {"logs": logs, "total": total, "limit": limit, "offset": offset}
