"""지수·기준 ETF 시세."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from research.data.krx import to_number
from research.paths import DATA_DIR

KODEX200_YF = "069500.KS"


def normalize_index_rows(raw: pd.DataFrame, index_name: str) -> pd.Series:
    """KRX KOSPI 시리즈 일별시세 원본 → 지정 지수의 종가 Series (날짜 인덱스)."""
    rows = raw[raw["IDX_NM"].str.strip() == index_name]
    closes = rows["CLSPRC_IDX"].map(to_number)
    closes.index = pd.to_datetime(rows["BAS_DD"], format="%Y%m%d")
    return closes.dropna().sort_index().rename(index_name)


def load_kodex200(start: str, end: str) -> pd.DataFrame:
    """KODEX 200 일봉 (분배금 재투자 수정주가, yfinance). parquet 캐시.

    단일 ETF라 생존 편향이 없고, 분배금을 세전으로 재투자하므로 기준 전략에 약간 유리하다
    (전략 판정에는 보수적인 방향).
    """
    path = DATA_DIR / "benchmark" / f"kodex200_{start}_{end}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    data = yf.download(KODEX200_YF, start=start, end=end, auto_adjust=True, progress=False)
    if data.empty:
        raise ValueError(f"No price data for {KODEX200_YF}")
    df = pd.DataFrame(
        {col.lower(): data[col].squeeze() for col in ("Open", "High", "Low", "Close", "Volume")}
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df
