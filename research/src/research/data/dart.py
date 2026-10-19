"""DART OpenAPI (opendart.fss.or.kr) 수집기 — 공시 목록, 현금배당.

- 일일 호출 한도 20,000회. 응답 status "000" 정상, "013" 조회 결과 없음.
- 공시 접수일(rcept_dt)은 날짜만 있고 시각이 없다 → 사용 측에서 다음 거래일부터 반영해야
  장 마감 후 공시를 당일 판단에 쓰는 미래 정보 누출을 막는다.
- 배당(alotMatter)은 2015 사업연도부터 제공. 2015 보고서의 전기·전전기 값으로 2013–2014를 채운다.
"""

from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import httpx
import pandas as pd

from research.data.krx import to_number
from research.paths import DATA_DIR

BASE_URL = "https://opendart.fss.or.kr/api/"
STATUS_OK = "000"
STATUS_NO_DATA = "013"
ANNUAL_REPORT = "11011"
FIRST_DIVIDEND_YEAR = 2015
# 주요사항보고(B), 거래소공시(I) — 악재성 공시는 대부분 여기 속한다
DISCLOSURE_TYPES = ("B", "I")
_PAGE_COUNT = 100
_REQUEST_INTERVAL_SEC = 0.1


class DartError(RuntimeError):
    pass


class DartClient:
    def __init__(
        self,
        api_key: str,
        cache_dir: Path = DATA_DIR / "dart",
        http: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise DartError("DART_API_KEY가 비어 있습니다 (research/.env)")
        self._key = api_key
        self._http = http or httpx.Client(base_url=BASE_URL, timeout=30)
        self._cache_dir = cache_dir
        self.calls = 0

    def _get(self, path: str, params: dict) -> httpx.Response:
        resp = self._http.get(path, params={"crtfc_key": self._key, **params})
        self.calls += 1
        resp.raise_for_status()
        time.sleep(_REQUEST_INTERVAL_SEC)
        return resp

    def _get_json(self, path: str, params: dict) -> dict:
        body = self._get(path, params).json()
        status = body.get("status")
        if status not in (STATUS_OK, STATUS_NO_DATA):
            raise DartError(f"{path} {params} → {status}: {body.get('message')}")
        return body

    def corp_codes(self) -> pd.DataFrame:
        """corp_code, corp_name, stock_code 전체 목록 (상장폐지 회사 포함)."""
        path = self._cache_dir / "corp_codes.parquet"
        if path.exists():
            return pd.read_parquet(path)
        payload = self._get("corpCode.xml", {}).content
        with zipfile.ZipFile(io.BytesIO(payload)) as zf:
            root = ElementTree.fromstring(zf.read(zf.namelist()[0]))
        df = pd.DataFrame(
            [
                {
                    "corp_code": el.findtext("corp_code", "").strip(),
                    "corp_name": el.findtext("corp_name", "").strip(),
                    "stock_code": el.findtext("stock_code", "").strip(),
                }
                for el in root.iter("list")
            ]
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        return df

    def disclosures(self, corp_code: str, start: str, end: str) -> pd.DataFrame:
        """한 회사의 공시 목록 (start/end: YYYYMMDD). 회사별로 캐시."""
        path = self._cache_dir / "disclosures" / f"{corp_code}_{start}_{end}.parquet"
        if path.exists():
            return pd.read_parquet(path)
        rows: list[dict] = []
        for pblntf_ty in DISCLOSURE_TYPES:
            page = 1
            while True:
                body = self._get_json(
                    "list.json",
                    {
                        "corp_code": corp_code,
                        "bgn_de": start,
                        "end_de": end,
                        "pblntf_ty": pblntf_ty,
                        "page_no": page,
                        "page_count": _PAGE_COUNT,
                    },
                )
                rows.extend(body.get("list") or [])
                if page >= int(body.get("total_page") or 1):
                    break
                page += 1
        df = pd.DataFrame(rows, columns=["corp_code", "report_nm", "rcept_no", "rcept_dt"])
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        return df

    def annual_dividends(self, corp_code: str, years: range) -> dict[int, float]:
        """사업연도 → 보통주 주당 현금배당금(원). 값이 없는 해는 빠진다."""
        path = self._cache_dir / "dividends" / f"{corp_code}.json"
        cached: dict[str, float | None] = json.loads(path.read_text()) if path.exists() else {}
        for year in years:
            report_year = max(year, FIRST_DIVIDEND_YEAR)
            column = {0: "thstrm", 1: "frmtrm", 2: "lwfr"}.get(report_year - year)
            key = str(year)
            if key in cached or column is None:
                continue
            body = self._get_json(
                "alotMatter.json",
                {
                    "corp_code": corp_code,
                    "bsns_year": str(report_year),
                    "reprt_code": ANNUAL_REPORT,
                },
            )
            cached[key] = parse_common_dps(body.get("list") or [], column)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cached))
        return {int(y): v for y, v in cached.items() if v is not None and int(y) in years}


def parse_common_dps(rows: list[dict], column: str) -> float | None:
    """alotMatter 응답에서 보통주 주당 현금배당금을 꺼낸다."""
    for row in rows:
        if "주당 현금배당금" in row.get("se", "") and row.get("stock_knd", "보통주") == "보통주":
            return to_number(row.get(column))
    return None


def map_corp_codes(stocks: pd.DataFrame, corp: pd.DataFrame) -> dict[str, str]:
    """종목코드 → corp_code. 상장폐지로 stock_code가 비어 있으면 회사명 일치로 보완."""
    by_stock = dict(zip(corp["stock_code"], corp["corp_code"], strict=True))
    by_name = corp.drop_duplicates("corp_name", keep=False)
    by_name = dict(zip(by_name["corp_name"], by_name["corp_code"], strict=True))
    mapping: dict[str, str] = {}
    for code, name in zip(stocks["code"], stocks["name"], strict=True):
        corp_code = by_stock.get(code) or by_name.get(name)
        if corp_code:
            mapping[code] = corp_code
    return mapping
