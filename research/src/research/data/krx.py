"""KRX OpenAPI (openapi.krx.co.kr) 수집기.

- 호출 1회 = 기준일자 하루치 전 종목. 그날 상장돼 있던 종목이 모두 들어 있어 시점별 유니버스와
  상장폐지 종목을 그대로 재현할 수 있다 (생존 편향 없음).
- 인증키는 요청 헤더 `AUTH_KEY`. HTTP 401은 대개 서비스별 "API 이용신청" 미승인이다.
- 값은 전부 문자열, 거래 없는 종목의 가격은 "" — 0이 아니라 None으로 읽는다.
- 직전 거래일 데이터는 오전 8시 이후 공개, 당일 데이터는 없다. 0행은 휴장일일 수 있다.
- 일일 호출 한도 10,000회 / 비상업적 이용, 제3자 제공 금지 — 원본은 커밋하지 않는다.
"""

from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pandas as pd
from loguru import logger

from research.paths import DATA_DIR

BASE_URL = "https://data-dbg.krx.co.kr/svc/apis/"
KOSPI_STOCKS = "sto/stk_bydd_trd"  # 유가증권 일별매매정보
KOSPI_INDEX = "idx/kospi_dd_trd"  # KOSPI 시리즈 일별시세정보

DAILY_CALL_LIMIT = 10_000
_REQUEST_INTERVAL_SEC = 0.1
# 이 날짜 이전의 0행 응답은 휴장일로 확정하고 캐시한다 (최근일은 미공개일 수 있어 재시도)
_EMPTY_FINAL_AFTER_DAYS = 2


class KrxError(RuntimeError):
    pass


def to_number(raw: object) -> float | None:
    """KRX 문자열 값을 숫자로. 빈 값·'-'는 None."""
    if raw is None:
        return None
    s = str(raw).replace(",", "").strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


class KrxClient:
    """서비스·기준일자별 응답을 parquet로 캐시하며 받아온다."""

    def __init__(
        self,
        auth_key: str,
        cache_dir: Path = DATA_DIR / "krx",
        http: httpx.Client | None = None,
        call_limit: int = DAILY_CALL_LIMIT,
    ) -> None:
        if not auth_key:
            raise KrxError("KRX_AUTH_KEY가 비어 있습니다 (research/.env)")
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=30)
        self._headers = {"AUTH_KEY": auth_key, "Accept": "application/json"}
        self._cache_dir = cache_dir
        self._call_limit = call_limit
        self.calls = 0

    def _cache_path(self, service: str, bas_dd: date) -> Path:
        return self._cache_dir / service.replace("/", "_") / f"{bas_dd:%Y%m%d}.parquet"

    def fetch_day(self, service: str, bas_dd: date) -> pd.DataFrame:
        """하루치 응답. 캐시가 있으면 호출하지 않는다."""
        path = self._cache_path(service, bas_dd)
        if path.exists():
            return pd.read_parquet(path)
        if self.calls >= self._call_limit:
            raise KrxError(f"일일 호출 한도 {self._call_limit}회 도달 — 내일 이어서 실행하세요")

        resp = self._http.get(service, params={"basDd": f"{bas_dd:%Y%m%d}"}, headers=self._headers)
        self.calls += 1
        if resp.status_code in (401, 403):
            raise KrxError(
                f"{service} 호출 거부 (HTTP {resp.status_code}) — openapi.krx.co.kr에서 "
                "해당 서비스의 'API 이용신청' 승인 여부를 확인하세요"
            )
        resp.raise_for_status()
        rows = (resp.json() if resp.content.strip() else {}).get("OutBlock_1") or []
        df = pd.DataFrame(rows, dtype=str)

        is_final = bas_dd <= date.today() - timedelta(days=_EMPTY_FINAL_AFTER_DAYS)
        if not df.empty or is_final:
            path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(path, index=False)
        time.sleep(_REQUEST_INTERVAL_SEC)
        return df

    def fetch_range(self, service: str, start: date, end: date) -> int:
        """start~end 평일을 모두 캐시에 채운다. 새로 호출한 횟수를 반환."""
        before = self.calls
        for day in pd.bdate_range(start, end):
            try:
                self.fetch_day(service, day.date())
            except httpx.HTTPError as e:
                logger.warning(f"{service} {day:%Y-%m-%d} 실패, 다음 실행에서 재시도: {e}")
        return self.calls - before

    def load_range(self, service: str, start: date, end: date) -> pd.DataFrame:
        """캐시된 일자 파일을 이어 붙인다 (호출하지 않음)."""
        frames = [
            pd.read_parquet(p)
            for p in sorted((self._cache_dir / service.replace("/", "_")).glob("*.parquet"))
            if start <= datetime.strptime(p.stem, "%Y%m%d").date() <= end
        ]
        frames = [f for f in frames if not f.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
