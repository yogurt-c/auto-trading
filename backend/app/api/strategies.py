"""Strategies API — CRUD, evaluate, dca-due."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.application.tools import (
    check_dca_due as _check_dca_due,
)
from app.application.tools import (
    evaluate_strategy as _evaluate_strategy,
)
from app.application.tools import (
    save_strategy as _save_strategy,
)
from app.infrastructure import repository as db

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/strategies")
def get_strategies(status: str | None = None):
    """전략 목록 반환. status 파라미터로 필터 가능."""
    return db.get_strategies(status)


class StrategyCreate(BaseModel):
    name: str
    strategy_type: str
    summary: str = ""
    ticker: str | None = None
    ai_rationale: str | None = None
    entry_price_drop_pct: float | None = None
    entry_rsi_below: float | None = None
    take_profit_pct: float | None = None
    stop_loss_pct: float | None = None
    sell_ratio: float | None = None
    dca_amount_usd: float | None = None
    dca_frequency_days: int | None = None
    max_position_usd: float | None = None
    strategy_id: int | None = None


@router.post("/strategies")
def save_strategy(req: StrategyCreate):
    """전략 생성 또는 업데이트."""
    return _save_strategy(**req.model_dump())


class StatusUpdate(BaseModel):
    status: str


@router.patch("/strategies/{strategy_id}/status")
def update_strategy_status(strategy_id: int, req: StatusUpdate):
    """전략 상태 변경: active | paused | completed."""
    result = db.update_strategy_status(strategy_id, req.status)
    if result:
        return {"success": True, "strategy": result}
    raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")


@router.delete("/strategies/{strategy_id}")
def delete_strategy(strategy_id: int):
    """전략 삭제."""
    ok = db.delete_strategy(strategy_id)
    if ok:
        return {"success": True}
    raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")


@router.get("/strategies/{strategy_id}/evaluate")
def evaluate_strategy(strategy_id: int):
    """전략 진입/청산 조건을 현재가 기준으로 평가."""
    return _evaluate_strategy(strategy_id)


@router.get("/strategies/{strategy_id}/dca-due")
def check_dca_due(strategy_id: int):
    """DCA 전략의 다음 매수 시점 여부 확인."""
    return _check_dca_due(strategy_id)
