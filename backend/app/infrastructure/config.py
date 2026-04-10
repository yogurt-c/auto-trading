"""Application settings backed by SQLite DB.

로드 순서: DB settings 테이블 (유일한 소스)
캐시: 모듈 레벨 변수 (_cache) — DB 접근이 필요할 때만 갱신
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select

REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "KIS_APP_KEY", "KIS_APP_SECRET", "KIS_ACCOUNT_NO")

_cache: Settings | None = None
_cache_lock = threading.Lock()


@dataclass
class Settings:
    anthropic_api_key: str = ""
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""  # 예: "12345678-01"
    kis_paper: bool = True  # True = 모의투자, False = 실전

    @property
    def is_configured(self) -> bool:
        return bool(
            self.anthropic_api_key
            and self.kis_app_key
            and self.kis_app_secret
            and self.kis_account_no
        )

    @property
    def missing_keys(self) -> list[str]:
        mapping = {
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "kis_app_key": "KIS_APP_KEY",
            "kis_app_secret": "KIS_APP_SECRET",
            "kis_account_no": "KIS_ACCOUNT_NO",
        }
        return [label for field, label in mapping.items() if not getattr(self, field)]


def _load_from_db() -> Settings | None:
    from .database import get_session
    from .models import Setting

    try:
        with get_session() as s:
            rows = s.execute(select(Setting)).scalars().all()
            data = {r.key.lower(): r.value for r in rows if r.value}
        return Settings(
            anthropic_api_key=data.get("anthropic_api_key", ""),
            kis_app_key=data.get("kis_app_key", ""),
            kis_app_secret=data.get("kis_app_secret", ""),
            kis_account_no=data.get("kis_account_no", ""),
            kis_paper=data.get("kis_paper", "true").lower() == "true",
        )
    except Exception as e:
        logger.error(f"DB에서 settings 로드 실패: {e}")
        return None  # 캐시하지 않음 — 다음 호출 시 재시도


def get_settings() -> Settings:
    """캐시된 설정 반환. 최초 호출 시에만 DB 조회. DB 실패 시 빈 Settings 반환(캐시 안 함)."""
    global _cache
    with _cache_lock:
        if _cache is None:
            result = _load_from_db()
            if result is not None:
                _cache = result
            else:
                return Settings()  # 실패 시 캐시하지 않고 빈 객체 반환
        return _cache


def reload_settings() -> Settings:
    """설정 저장 후 캐시 갱신 시 호출."""
    global _cache
    with _cache_lock:
        result = _load_from_db()
        if result is not None:
            _cache = result
        else:
            logger.warning("reload_settings: DB 조회 실패 — 이전 캐시를 유지합니다")
        return _cache if _cache is not None else Settings()
