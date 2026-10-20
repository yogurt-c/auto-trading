"""KRX 일별 원본 → 종목별 시세 패널 + 수정주가 계수.

KRX 일별 데이터는 수정주가가 아니다. 분할·병합·무상증자·권리락이 있으면 그날의 기준가가
조정되므로, `기준가 = 종가 - 전일대비`를 직전 종가와 비교해 조정 계수를 복원한다.
현금배당은 기준가를 조정하지 않으므로 계수에 들어가지 않는다 (KIS 수정주가와 같은 의미).
"""

from __future__ import annotations

import pandas as pd

from research.data.krx import to_number

_STOCK_COLUMNS = {
    "BAS_DD": "date",
    "ISU_CD": "code",
    "ISU_NM": "name",
    "TDD_OPNPRC": "open",
    "TDD_HGPRC": "high",
    "TDD_LWPRC": "low",
    "TDD_CLSPRC": "close",
    "CMPPREVDD_PRC": "change",
    "ACC_TRDVOL": "volume",
    "MKTCAP": "market_cap",
    "LIST_SHRS": "shares",
}
_NUMERIC = ["open", "high", "low", "close", "change", "volume", "market_cap", "shares"]
_PRICE_COLUMNS = ["open", "high", "low", "close"]

# 기준가/직전 종가 비율이 이만큼 벗어나야 조정 이벤트로 본다 (호가 단위 반올림 노이즈 제외)
ADJUSTMENT_TOLERANCE = 0.005


def normalize_stock_rows(raw: pd.DataFrame) -> pd.DataFrame:
    """KRX 유가증권 일별매매정보 원본 행 → (date, code) 정렬된 수치 패널."""
    df = raw[list(_STOCK_COLUMNS)].rename(columns=_STOCK_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    # 표준코드(KR7005930003)로 올 경우 단축코드(005930)로 통일
    df["code"] = df["code"].str.strip().map(lambda c: c[3:9] if len(c) == 12 else c)
    for col in _NUMERIC:
        df[col] = df[col].map(to_number)
    # 거래가 없으면 가격이 비거나 0 — 결측으로 둔다
    for col in _PRICE_COLUMNS:
        df.loc[df[col] <= 0, col] = None
    return df.sort_values(["code", "date"]).reset_index(drop=True)


def add_adjustment(panel: pd.DataFrame) -> pd.DataFrame:
    """조정 계수 컬럼을 추가한 새 DataFrame을 반환한다.

    - `factor`: t일 이벤트 계수 = 기준가_t / 직전 유효 종가 (이벤트가 없으면 1.0)
    - `adj_ratio`: t일 이후(t 제외) 이벤트 계수의 곱. `가격 * adj_ratio`가 최신 기준 수정주가
    """
    out = panel.sort_values(["code", "date"]).copy()
    prev_close = out.groupby("code")["close"].transform(lambda s: s.ffill().shift(1))
    base = out["close"] - out["change"]
    raw_factor = base / prev_close
    is_event = (raw_factor - 1).abs() > ADJUSTMENT_TOLERANCE
    out["factor"] = raw_factor.where(is_event & raw_factor.gt(0), 1.0).fillna(1.0)

    def _ratio_after(f: pd.Series) -> pd.Series:
        return f[::-1].cumprod()[::-1] / f

    out["adj_ratio"] = out.groupby("code")["factor"].transform(_ratio_after)
    return out


def adjusted_window(rows: pd.DataFrame) -> pd.DataFrame:
    """한 종목의 과거 구간(오래된 순, 마지막 행 = 판단일)을 판단일 기준 수정주가로 변환.

    판단일 이후의 이벤트는 반영하지 않는다 — 마지막 행의 가격이 그날 실제 가격과 같다.
    """
    scale = rows["adj_ratio"] / rows["adj_ratio"].iloc[-1]
    out = rows[["date", *_PRICE_COLUMNS, "volume"]].copy()
    for col in _PRICE_COLUMNS:
        out[col] = out[col] * scale
    out["volume"] = out["volume"] / scale
    return out.set_index("date")
