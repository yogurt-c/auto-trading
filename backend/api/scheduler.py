"""Scheduler + Settings API."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from infrastructure import repository as db
from application.scheduler import ensure_started, get_status

router = APIRouter()


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
    from infrastructure.config import get_settings
    from infrastructure import alpaca_client

    s = get_settings()
    if not s.is_configured:
        keys = ", ".join(s.missing_keys)
        return {"ok": False, "reason": "missing", "message": f"미설정 키: {keys}"}

    try:
        alpaca_client.get_account()
        return {"ok": True, "reason": "ok", "message": ""}
    except ValueError as e:
        return {"ok": False, "reason": "missing", "message": str(e)}
    except Exception as e:
        err = str(e)
        if "unauthorized" in err.lower():
            return {"ok": False, "reason": "invalid", "message": "Alpaca API 키가 유효하지 않습니다. Settings 페이지에서 확인해 주세요."}
        return {"ok": False, "reason": "invalid", "message": f"Alpaca 연결 실패: {err}"}


@router.get("/settings")
def get_all_settings():
    """모든 설정 키-값 반환."""
    settings = db.get_all_settings()
    return {"settings": settings}


class SettingValue(BaseModel):
    value: str


@router.put("/settings/{key}")
def save_setting(key: str, req: SettingValue):
    """설정 저장. API 키 변경 시 클라이언트 리로드."""
    db.save_setting(key, req.value)
    if key in ("ANTHROPIC_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "ALPACA_PAPER"):
        from infrastructure.config import reload_settings
        from infrastructure.alpaca_client import reset_client
        reload_settings()
        reset_client()
    return {"success": True}
