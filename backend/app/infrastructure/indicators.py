"""기술지표 계산 함수 모음 (pandas Series → float/tuple).

모든 함수는 I/O 없이 순수 계산만 수행합니다.
데이터 부족 등으로 계산 불가 시 None 또는 None 튜플을 반환합니다.
"""

from __future__ import annotations

import math

import pandas as pd


def calc_rsi(closes: pd.Series, period: int = 14) -> float | None:
    """Wilder RSI. 데이터 부족 시 None 반환."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi_series = 100 - 100 / (1 + rs)
    val = float(rsi_series.iloc[-1])
    return None if math.isnan(val) else val


def calc_sma(closes: pd.Series, period: int) -> float | None:
    """단순 이동평균. 데이터가 period보다 짧으면 None."""
    if len(closes) < period:
        return None
    val = float(closes.rolling(period).mean().iloc[-1])
    return None if math.isnan(val) else val


def calc_ema(closes: pd.Series, period: int) -> float | None:
    """지수 이동평균. 데이터가 period보다 짧으면 None."""
    if len(closes) < period:
        return None
    val = float(closes.ewm(span=period, adjust=False).mean().iloc[-1])
    return None if math.isnan(val) else val


def calc_macd(
    closes: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float | None, float | None, float | None]:
    """MACD 라인, 시그널 라인, 히스토그램 반환.

    Returns:
        (macd_line, signal_line, histogram) — 계산 불가 시 (None, None, None)
    """
    if len(closes) < slow + signal:
        return None, None, None
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    m = float(macd_line.iloc[-1])
    s = float(signal_line.iloc[-1])
    h = float(histogram.iloc[-1])

    if math.isnan(m) or math.isnan(s) or math.isnan(h):
        return None, None, None
    return m, s, h


def calc_bollinger(
    closes: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[float | None, float | None, float | None]:
    """볼린저 밴드 (upper, middle, lower) 반환.

    Returns:
        (upper, middle, lower) — 계산 불가 시 (None, None, None)
    """
    if len(closes) < period:
        return None, None, None
    middle = closes.rolling(period).mean()
    std = closes.rolling(period).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std

    u = float(upper.iloc[-1])
    m = float(middle.iloc[-1])
    lo = float(lower.iloc[-1])

    if math.isnan(u) or math.isnan(m) or math.isnan(lo):
        return None, None, None
    return u, m, lo


def calc_disparity(closes: pd.Series, period: int = 20) -> float | None:
    """이격도: (현재가 / SMA - 1) * 100 (%).

    양수 = 이동평균 위, 음수 = 이동평균 아래.
    """
    sma = calc_sma(closes, period)
    if sma is None or sma == 0:
        return None
    return (float(closes.iloc[-1]) / sma - 1) * 100


def calc_atr(
    highs: pd.Series,
    lows: pd.Series,
    closes: pd.Series,
    period: int = 14,
) -> float | None:
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    prev_close = closes.shift(1)
    tr = pd.concat(
        [
            highs - lows,
            (highs - prev_close).abs(),
            (lows - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean()
    val = float(atr.iloc[-1])
    return None if math.isnan(val) else val


def calc_volume_ratio(volumes: pd.Series, period: int = 20) -> float | None:
    """거래량 비율: 현재 거래량 / 최근 N일 평균 거래량.

    1.0 = 평균, 2.0 = 평균의 2배.
    """
    if len(volumes) < period + 1:
        return None
    mean_vol = float(volumes.iloc[-period - 1 : -1].mean())
    if mean_vol == 0:
        return None
    val = float(volumes.iloc[-1]) / mean_vol
    return None if math.isnan(val) else val
