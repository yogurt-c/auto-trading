"""Application settings backed by SQLite DB.

로드 순서: DB settings 테이블 (유일한 소스)
캐시: 모듈 레벨 변수 (_cache) — DB 접근이 필요할 때만 갱신
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

REQUIRED_KEYS = ("ANTHROPIC_API_KEY", "ALPACA_API_KEY", "ALPACA_SECRET_KEY")

_cache: Settings | None = None


@dataclass
class Settings:
    anthropic_api_key: str = ""
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_paper: bool = True

    @property
    def is_configured(self) -> bool:
        return bool(self.anthropic_api_key and self.alpaca_api_key and self.alpaca_secret_key)

    @property
    def missing_keys(self) -> list[str]:
        mapping = {
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "alpaca_api_key": "ALPACA_API_KEY",
            "alpaca_secret_key": "ALPACA_SECRET_KEY",
        }
        return [label for field, label in mapping.items() if not getattr(self, field)]


def _load_from_db() -> Settings:
    from .database import get_session
    from .models import Setting

    try:
        with get_session() as s:
            rows = s.execute(select(Setting)).scalars().all()
            data = {r.key.lower(): r.value for r in rows if r.value}
        return Settings(
            anthropic_api_key=data.get("anthropic_api_key", ""),
            alpaca_api_key=data.get("alpaca_api_key", ""),
            alpaca_secret_key=data.get("alpaca_secret_key", ""),
            alpaca_paper=data.get("alpaca_paper", "true").lower() == "true",
        )
    except Exception:
        return Settings()


def get_settings() -> Settings:
    """캐시된 설정 반환. 최초 호출 시에만 DB 조회."""
    global _cache
    if _cache is None:
        _cache = _load_from_db()
    return _cache


def reload_settings() -> Settings:
    """설정 저장 후 캐시 갱신 시 호출."""
    global _cache
    _cache = _load_from_db()
    return _cache
