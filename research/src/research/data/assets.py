"""R2 자산 시세 — 국내 ETF(yfinance)와 합성 미국 지수 ETF(S&P500 총수익 x 원/달러).

모든 자산은 한국 거래일 달력(KRX 코스피 200 일자)에 맞춘 open/high/low/close DataFrame이다.
"""

from __future__ import annotations

from io import StringIO

import httpx
import pandas as pd
import yfinance as yf

from research.paths import DATA_DIR

ASSET_DIR = DATA_DIR / "assets"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
_PRICE_COLUMNS = ["open", "high", "low", "close"]

# 하루 급등락 후 다음 날 되돌아오는 단일 오류 틱 (예: 국고채3년 2010-02-09 +14%)
SPIKE_THRESHOLD = 0.05
SPIKE_REVERT_RATIO = 0.8


def _cached(name: str, fetch) -> pd.DataFrame:
    path = ASSET_DIR / f"{name}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    df = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return df


def fetch_yf(ticker: str, start: str, end: str) -> pd.DataFrame:
    """yfinance 일봉 (분배금 재투자 수정주가). 소문자 컬럼."""

    def fetch() -> pd.DataFrame:
        data = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
        if data.empty:
            raise ValueError(f"No price data for {ticker}")
        return pd.DataFrame(
            {col.lower(): data[col].squeeze() for col in ("Open", "High", "Low", "Close")}
        )

    return _cached(f"{ticker.replace('^', '').replace('.', '_')}_{start}", fetch)


def fetch_fred(series: str, start: str, end: str) -> pd.Series:
    def fetch() -> pd.DataFrame:
        resp = httpx.get(FRED_URL, params={"id": series, "cosd": start, "coed": end}, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), parse_dates=["observation_date"], na_values=".")
        return df.set_index("observation_date").rename(columns={series: "value"})

    return _cached(f"fred_{series}_{start}", fetch)["value"].dropna()


def remove_spikes(df: pd.DataFrame) -> pd.DataFrame:
    """종가가 하루만 튀었다 되돌아온 행을 전날 값으로 바꾼 새 DataFrame."""
    out = df.copy()
    r = out["close"].pct_change()
    is_spike = (r.abs() > SPIKE_THRESHOLD) & (
        (-r.shift(-1) / r) > SPIKE_REVERT_RATIO  # 다음 날 반대 방향으로 대부분 되돌림
    )
    for day in out.index[is_spike.fillna(False)]:
        prev = out.index[out.index.get_loc(day) - 1]
        out.loc[day, _PRICE_COLUMNS] = out.loc[prev, "close"]
    return out


def align_to_calendar(df: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """한국 거래일에 맞춘다. 빠진 날은 전날 종가로 채운다 (거래 없음 = 시고저종 동일)."""
    out = df.reindex(calendar)
    close = out["close"].ffill()
    for col in _PRICE_COLUMNS:
        out[col] = out[col].fillna(close)
    return out


def leveraged_index(
    total_return: pd.Series, rate_pct: pd.Series, leverage: float, annual_drag: float
) -> pd.Series:
    """일간 재조정 레버리지 지수 (미국 거래일 기준, 시작값 1)."""
    r = total_return.pct_change().fillna(0.0)
    # 월별·휴일 결측 금리는 직전 값으로 (거래일과 날짜가 안 겹쳐도 되도록 합집합에서 채움)
    rate = rate_pct.reindex(rate_pct.index.union(r.index)).ffill().bfill().reindex(r.index)
    rf = (rate / 100) / 252
    daily = leverage * r - (leverage - 1) * rf - annual_drag / 252
    daily.iloc[0] = 0.0
    return (1 + daily).cumprod()


def synthetic_krw_etf(
    usd_index: pd.Series, fx: pd.Series, calendar: pd.DatetimeIndex, base: float = 10_000.0
) -> pd.DataFrame:
    """한국 거래일 d 가격 = d 이전 마지막 미국 종가 x d 이전 마지막 환율. 시고저종 동일."""
    us = usd_index.sort_index()
    fx = fx.sort_index()
    us_pos = us.index.searchsorted(calendar, side="left") - 1
    fx_pos = fx.index.searchsorted(calendar, side="left") - 1
    valid = (us_pos >= 0) & (fx_pos >= 0)
    price = pd.Series(float("nan"), index=calendar)
    price[valid] = us.to_numpy()[us_pos[valid]] * fx.to_numpy()[fx_pos[valid]]
    price = price / price.dropna().iloc[0] * base
    return pd.DataFrame(dict.fromkeys(_PRICE_COLUMNS, price))


def us_signal_series(index_close: pd.Series, calendar: pd.DatetimeIndex) -> pd.Series:
    """한국 거래일 d에서 알 수 있는 미국 지수 값 (d 이전 마지막 미국 종가)."""
    s = index_close.sort_index()
    pos = s.index.searchsorted(calendar, side="left") - 1
    out = pd.Series(float("nan"), index=calendar)
    out[pos >= 0] = s.to_numpy()[pos[pos >= 0]]
    return out


def load_assets(
    cfg: dict, calendar: pd.DatetimeIndex, start: str, end: str
) -> dict[str, pd.DataFrame]:
    """r2_strategies.yaml의 assets 정의 → 자산명별 OHLC (한국 거래일)."""
    fx = fetch_fred(cfg["synthetic"]["fx"], start, end)
    rate = fetch_fred(cfg["synthetic"]["rate"], start, end)
    out = {}
    for name, spec in cfg["assets"].items():
        if spec["source"] == "yfinance":
            raw = remove_spikes(fetch_yf(spec["ticker"], start, end))
            out[name] = align_to_calendar(raw, calendar)
        else:
            tr = fetch_yf(spec["index"], start, end)["close"]
            usd = leveraged_index(tr, rate, spec["leverage"], spec["annual_drag"])
            out[name] = synthetic_krw_etf(usd, fx, calendar)
    return out
