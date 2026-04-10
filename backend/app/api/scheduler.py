"""Scheduler + Settings API."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.application.scheduler import ensure_started, get_status
from app.infrastructure import kis_client
from app.infrastructure import repository as db
from app.infrastructure.config import get_settings

_HIDDEN_KEYS = {"__SECRET_KEY__", "APP_PASSWORD_HASH"}
_WRITE_BLOCKED_KEYS = {"__SECRET_KEY__", "APP_PASSWORD_HASH"}
_MASKED_KEYS = {
    "KIS_PAPER_APP_KEY",
    "KIS_PAPER_APP_SECRET",
    "KIS_REAL_APP_KEY",
    "KIS_REAL_APP_SECRET",
    "ANTHROPIC_API_KEY",
}

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/scheduler/status")
def scheduler_status():
    """현재 스케줄러 상태 반환."""
    status = get_status()
    return {
        "running": status["running"],
        "next_run": status["next_run"].isoformat() if status["next_run"] else None,
        "market_open": status["market_open"],
    }


@router.get("/scheduler/runs")
def get_scheduler_runs(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """스케줄러 실행 이력 반환 (페이징 지원)."""
    runs = db.get_scheduler_runs(limit=limit, offset=offset)
    total = db.count_scheduler_runs()
    return {"runs": runs, "total": total, "limit": limit, "offset": offset}


@router.post("/scheduler/trigger")
def trigger_scheduler():
    """스케줄러 설정 재적용 (시작/중지/재구성)."""
    ensure_started()
    return {"success": True}


@router.get("/settings/status")
def settings_status():
    """API 키 유효성 검증 (미설정 / 인증실패 / 정상).

    응답: { ok: bool, reason: 'ok'|'missing'|'invalid', message: str }
    """
    s = get_settings()
    if not s.is_configured:
        keys = ", ".join(s.missing_keys)
        return {"ok": False, "reason": "missing", "message": f"미설정 키: {keys}"}

    try:
        kis_client.get_account()
        if not s.kis_paper:
            return {
                "ok": False,
                "reason": "live_trading_warning",
                "message": (
                    "경고: KIS_PAPER가 false로 설정되어 있습니다. "
                    "실전 계좌로 실제 주문이 실행됩니다. 주의하세요."
                ),
            }
        return {"ok": True, "reason": "ok", "message": ""}
    except ValueError as e:
        return {"ok": False, "reason": "missing", "message": str(e)}
    except Exception as e:
        err = str(e)
        if "인증" in err or "token" in err.lower() or "unauthorized" in err.lower():
            return {
                "ok": False,
                "reason": "invalid",
                "message": "KIS API 키가 유효하지 않습니다. Settings 페이지에서 확인해 주세요.",
            }
        return {"ok": False, "reason": "invalid", "message": f"KIS 연결 실패: {err}"}


@router.get("/settings")
def get_all_settings():
    """모든 설정 키-값 반환. 민감 키는 마스킹·제외."""
    raw = db.get_all_settings()
    settings = {}
    for key, value in raw.items():
        if key in _HIDDEN_KEYS:
            continue
        if key in _MASKED_KEYS and value:
            settings[key] = "****"
        else:
            settings[key] = value
    return {"settings": settings}


class SettingValue(BaseModel):
    value: str


@router.put("/settings/{key}")
def save_setting(key: str, req: SettingValue):
    """설정 저장. API 키 변경 시 클라이언트 리로드."""
    if key in _WRITE_BLOCKED_KEYS:
        raise HTTPException(status_code=403, detail="해당 키는 직접 수정할 수 없습니다")
    db.save_setting(key, req.value)
    if key in (
        "ANTHROPIC_API_KEY",
        "KIS_PAPER_APP_KEY",
        "KIS_PAPER_APP_SECRET",
        "KIS_PAPER_ACCOUNT_NO",
        "KIS_REAL_APP_KEY",
        "KIS_REAL_APP_SECRET",
        "KIS_REAL_ACCOUNT_NO",
        "KIS_PAPER",
    ):
        from app.infrastructure.config import reload_settings

        reload_settings()
        kis_client.reset_client()
    if key in ("scheduler_interval_minutes", "scheduler_enabled"):
        ensure_started()
    return {"success": True}
