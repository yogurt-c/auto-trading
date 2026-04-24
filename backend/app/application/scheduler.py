"""APScheduler 기반 자동 매매 스케줄러 싱글톤."""

from __future__ import annotations

import threading
from datetime import datetime, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.infrastructure.timezone import now_kst

_KST = ZoneInfo("Asia/Seoul")
_ET = ZoneInfo("America/New_York")

_KRX_OPEN = time(9, 0)
_KRX_CLOSE = time(15, 30)
_NYSE_OPEN = time(9, 30)
_NYSE_CLOSE = time(16, 0)


def is_krx_open(now: datetime | None = None) -> bool:
    """KRX 장 시간 여부 확인. 평일 09:00~15:30 KST."""
    now_kst_dt = (now or datetime.now(_KST)).astimezone(_KST)
    return now_kst_dt.weekday() < 5 and _KRX_OPEN <= now_kst_dt.time() < _KRX_CLOSE


def is_nyse_open(now: datetime | None = None) -> bool:
    """NYSE 장 시간 여부 확인. 평일 09:30~16:00 ET."""
    now_et = (now or datetime.now(_ET)).astimezone(_ET)
    return now_et.weekday() < 5 and _NYSE_OPEN <= now_et.time() < _NYSE_CLOSE


def _is_market_open() -> bool:
    """KRX 또는 NYSE 중 하나라도 열려 있으면 True."""
    return is_krx_open() or is_nyse_open()


_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()
# APScheduler의 max_instances=1은 스케줄 잡끼리만 직렬화한다.
# trigger_now()가 생성하는 raw 스레드는 이를 우회하므로 별도 Lock으로 전체 직렬화.
_job_lock = threading.Lock()

DEFAULT_INTERVAL_MINUTES = 30


def _job() -> None:
    if not _job_lock.acquire(blocking=False):
        logger.info("scheduler job already running — skipping overlapping trigger")
        return
    try:
        _job_body()
    finally:
        _job_lock.release()


def _job_body() -> None:
    """실제 스케줄러 작업 본문. _job()에 의해 단일 스레드에서 실행된다."""
    from app.infrastructure.repository import (
        add_scheduler_run,
        get_strategies,
        update_scheduler_run,
        update_strategies_last_checked,
    )

    from .agent import run_trade_executor

    logger.debug("scheduler job fired")

    # 장 외 시간에는 그냥 종료
    krx_open = is_krx_open()
    nyse_open = is_nyse_open()
    if not (krx_open or nyse_open):
        logger.info("market closed — run skipped")
        return
    logger.info(f"market open — KRX={krx_open}, NYSE={nyse_open}")

    # limit order 체결분 포함 최신 포지션으로 갱신 + 미결 주문 상태 동기화
    try:
        from app.application.tools import sync_pending_orders
        from app.infrastructure.kis_client import sync_positions

        sync_positions()
        logger.info("holdings synced from KIS at job start")

        sync_result = sync_pending_orders()
        logger.info(
            f"pending orders synced: updated={sync_result['updated']} "
            f"still_pending={sync_result['still_pending']} "
            f"errors={len(sync_result['errors'])}"
        )
        for err in sync_result["errors"]:
            logger.warning(f"sync_pending error: {err}")
    except Exception as e:
        logger.warning(f"pre-job KIS sync failed — job aborted: {e}")
        run = add_scheduler_run()
        update_scheduler_run(
            run["id"],
            finished_at=now_kst(),
            status="failed",
            error_message=f"pre-sync failed: {e}",
        )
        return

    run = add_scheduler_run()  # status='running'
    ids: list[int] = []
    success = False
    summary_text: str | None = None
    error_msg: str | None = None
    try:
        active = get_strategies(status="active")
        markets_open = [m for m, flag in (("KR", krx_open), ("US", nyse_open)) if flag]
        eligible = [s for s in active if s["market"] in markets_open]
        ids = [s["id"] for s in eligible]
        if not ids:
            logger.info(f"no active strategies for open markets {markets_open} — run skipped")
            summary_text = f"열린 시장({', '.join(markets_open)})에 해당하는 활성 전략 없음"
            success = True
        else:
            logger.info(
                f"trade executor started — {len(ids)} strategies for markets {markets_open}"
            )
            summary_text = run_trade_executor(markets_open=markets_open)
            update_strategies_last_checked(ids)
            success = True
        logger.info(f"trade executor completed — run_id={run['id']}, strategies={len(ids)}")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"trade executor failed: {e}")
    finally:
        try:
            update_scheduler_run(
                run["id"],
                finished_at=now_kst(),
                status="success" if success else "failed",
                strategies_checked=len(ids) if success else 0,
                summary=summary_text,
                error_message=error_msg,
            )
        except Exception as upd_err:
            logger.error(f"failed to update scheduler_run {run['id']}: {upd_err}")


def ensure_started() -> None:
    """설정 기반으로 스케줄러 시작/중지/재구성. app.py 재실행마다 호출."""
    global _scheduler
    from app.infrastructure.repository import get_setting

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
                    logger.info(f"scheduler rescheduled to {interval}min")
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
        logger.info(f"scheduler started, interval={interval}min")


def trigger_now() -> None:
    """스케줄러 작업 즉시 실행 (백그라운드 스레드)."""
    t = threading.Thread(target=_job, daemon=True, name="manual_trigger")
    t.start()
    logger.info("manual scheduler trigger started")


def _stop() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler stopped")


def get_status() -> dict:
    """현재 스케줄러 상태 반환. UI에서 표시용."""
    krx_open = is_krx_open()
    nyse_open = is_nyse_open()
    if _scheduler and _scheduler.running:
        job = _scheduler.get_job("trade_executor")
        next_run = job.next_run_time if job else None
        return {"running": True, "next_run": next_run, "krx_open": krx_open, "nyse_open": nyse_open}
    return {"running": False, "next_run": None, "krx_open": krx_open, "nyse_open": nyse_open}
