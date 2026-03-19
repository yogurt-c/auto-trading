"""Trading API — Alpaca account, orders, logs."""


from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.application.tools import place_order as _place_order
from app.infrastructure import alpaca_client
from app.infrastructure import repository as db

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/trading/account")
def get_account():
    """Alpaca 계좌 정보 및 보유 포지션 반환."""
    try:
        account = alpaca_client.get_account()
        positions = alpaca_client.get_positions()
        return {"account": account, "positions": positions}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        err_str = str(e)
        if "unauthorized" in err_str.lower():
            raise HTTPException(
                status_code=401,
                detail="Alpaca API 인증 실패. Settings 페이지에서 API 키를 확인해 주세요.",
            )
        raise HTTPException(status_code=503, detail=f"Alpaca API 연결 실패: {err_str}")


class OrderRequest(BaseModel):
    ticker: str
    side: str
    qty: float
    order_type: str = "market"
    limit_price: float | None = None
    strategy_id: int | None = None
    ai_reasoning: str | None = None
    max_position_usd: float | None = None


@router.post("/trading/orders")
def place_order(req: OrderRequest):
    """Alpaca paper trading 주문 실행."""
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
