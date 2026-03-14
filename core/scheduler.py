"""APScheduler 기반 자동 매매 스케줄러 싱글톤."""

from __future__ import annotations

import threading
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler

_ET = ZoneInfo("America/New_York")
_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE = time(16, 0)


def _is_market_open() -> bool:
    """NYSE 장 시간 여부 확인 (평일 09:30~16:00 ET)."""
    now = datetime.now(_ET)
    if now.weekday() >= 5:  # 토(5)·일(6) 제외
        return False
    return _MARKET_OPEN <= now.time() < _MARKET_CLOSE

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()

DEFAULT_INTERVAL_MINUTES = 30


def _job() -> None:
    # 장 외 시간에는 API 호출 없이 조용히 종료
    if not _is_market_open():
        return

    from .portfolio import (
        add_scheduler_run,
        get_strategies,
        update_scheduler_run,
        update_strategies_last_checked,
    )
    from .agent import run_trade_executor

    run = add_scheduler_run()  # status='running'
    try:
        active = get_strategies(status="active")
        ids = [s["id"] for s in active]
        summary = run_trade_executor()

        update_strategies_last_checked(ids)
        update_scheduler_run(
            run["id"],
            finished_at=datetime.now(),
            status="success",
            strategies_checked=len(ids),
            summary=summary,
        )
    except Exception as e:
        update_scheduler_run(
            run["id"],
            finished_at=datetime.now(),
            status="failed",
            error_message=str(e),
        )


def ensure_started() -> None:
    """설정 기반으로 스케줄러 시작/중지/재구성. app.py 재실행마다 호출."""
    global _scheduler
    from .portfolio import get_setting

    enabled = get_setting("scheduler_enabled") == "true"
    interval_raw = get_setting("scheduler_interval_minutes")
    interval = int(interval_raw) if interval_raw else DEFAULT_INTERVAL_MINUTES

    with _lock:
        if not enabled:
            _stop()
            return
        if _scheduler and _scheduler.running:
            job = _scheduler.get_job("trade_executor")
            if job:
                current_interval = int(job.trigger.interval.total_seconds() // 60)
                if current_interval != interval:
                    job.reschedule("interval", minutes=interval)
            return
        # 새로 시작
        _scheduler = BackgroundScheduler(daemon=True)
        _scheduler.add_job(
            _job,
            "interval",
            minutes=interval,
            id="trade_executor",
            max_instances=1,
            coalesce=True,
        )
        _scheduler.start()


def _stop() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_status() -> dict:
    """현재 스케줄러 상태 반환. UI에서 표시용."""
    market_open = _is_market_open()
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("trade_executor")
        next_run = job.next_run_time if job else None
        return {"running": True, "next_run": next_run, "market_open": market_open}
    return {"running": False, "next_run": None, "market_open": market_open}
