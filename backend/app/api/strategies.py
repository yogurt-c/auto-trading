"""Strategies API — CRUD, evaluate, dca-due."""

from typing import Literal

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
def get_strategies(
    status: Literal["active", "paused", "completed"] | None = None,
):
    """전략 목록 반환. status 파라미터로 필터 가능."""
    return db.get_strategies(status)


class StrategyCreate(BaseModel):
    name: str
    strategy_type: Literal["dca", "momentum", "value", "stop_loss", "take_profit", "custom"]
    description: str = ""
    ticker: str | None = None
    ai_rationale: str | None = None
    market: Literal["KR", "US"] = "US"
    currency: Literal["KRW", "USD"] = "USD"
    entry_price_drop_pct: float | None = None
    entry_rsi_below: float | None = None
    take_profit_pct: float | None = None
    stop_loss_pct: float | None = None
    sell_ratio: float | None = None
    dca_amount: float | None = None
    dca_frequency_days: int | None = None
    max_position: float | None = None
    # 기술지표 기반 진입 조건
    entry_bb_lower_touch: bool | None = None
    entry_macd_hist_positive: bool | None = None
    entry_disparity_below: float | None = None
    entry_volume_surge: float | None = None
    entry_sma_cross: int | None = None
    strategy_id: int | None = None


@router.post("/strategies")
def save_strategy(req: StrategyCreate):
    """전략 생성 또는 업데이트."""
    try:
        return _save_strategy(**req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class StatusUpdate(BaseModel):
    status: Literal["active", "paused", "completed"]


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


_STRATEGY_PRESETS = [
    {
        "name": "RSI 과매도 + 볼린저 하단",
        "strategy_type": "value",
        "description": "RSI 30 이하이면서 볼린저 하단 터치 시 진입. 과매도 구간 반등 전략.",
        "risk": "low",
        "entry_rsi_below": 30.0,
        "entry_bb_lower_touch": True,
        "take_profit_pct": 10.0,
        "stop_loss_pct": -7.0,
    },
    {
        "name": "MACD 히스토그램 양전환",
        "strategy_type": "momentum",
        "description": "MACD 히스토그램이 음수에서 양수로 전환 시 진입. 추세 전환 포착.",
        "risk": "medium",
        "entry_macd_hist_positive": True,
        "take_profit_pct": 15.0,
        "stop_loss_pct": -8.0,
    },
    {
        "name": "이격도 과매도 반등",
        "strategy_type": "value",
        "description": "20일 이격도 -5% 이하 시 진입. 단기 평균 대비 과매도 구간.",
        "risk": "low",
        "entry_disparity_below": -5.0,
        "take_profit_pct": 5.0,
        "stop_loss_pct": -10.0,
    },
    {
        "name": "거래량 급증 모멘텀",
        "strategy_type": "momentum",
        "description": "거래량이 20일 평균의 2배 이상 급등 시 진입. 수급 폭발 포착.",
        "risk": "high",
        "entry_volume_surge": 2.0,
        "take_profit_pct": 20.0,
        "stop_loss_pct": -10.0,
    },
    {
        "name": "SMA20 돌파",
        "strategy_type": "momentum",
        "description": "현재가가 20일 이동평균선 위에 있을 때 진입. 단기 추세 추종.",
        "risk": "medium",
        "entry_sma_cross": 20,
        "take_profit_pct": 10.0,
        "stop_loss_pct": -5.0,
    },
    {
        "name": "DCA 기본",
        "strategy_type": "dca",
        "description": "정액 주기 매수. 시장 타이밍 무관, 평균단가 분산 전략.",
        "risk": "low",
        "dca_frequency_days": 7,
        "take_profit_pct": 20.0,
        "stop_loss_pct": -20.0,
    },
]


@router.get("/strategies/presets")
def get_strategy_presets():
    """검증된 전략 템플릿 목록 반환. 선택 시 권장 파라미터를 자동 입력할 수 있습니다."""
    return _STRATEGY_PRESETS


@router.get("/strategies/{strategy_id}/evaluate")
def evaluate_strategy(strategy_id: int):
    """전략 진입/청산 조건을 현재가 기준으로 평가."""
    return _evaluate_strategy(strategy_id)


@router.get("/strategies/{strategy_id}/dca-due")
def check_dca_due(strategy_id: int):
    """DCA 전략의 다음 매수 시점 여부 확인."""
    return _check_dca_due(strategy_id)
