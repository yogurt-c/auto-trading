"""실시간 시세 조회 (Yahoo Finance)."""

from __future__ import annotations

import re
from typing import Literal

import pandas as pd
import yfinance as yf

# KR 티커: 6자리 숫자 (예: 005930, 035720)
_KR_TICKER_RE = re.compile(r"^\d{6}$")


def _to_yf_ticker(ticker: str) -> str:
    """KR 6자리 숫자 티커에 .KS 접미사를 추가합니다."""
    return f"{ticker}.KS" if _KR_TICKER_RE.match(ticker) else ticker


from app.domain.trading_strategy.value_objects import MarketData
from app.infrastructure.indicators import (
    calc_atr,
    calc_bollinger,
    calc_disparity,
    calc_ema,
    calc_macd,
    calc_rsi,
    calc_sma,
    calc_volume_ratio,
)

# yfinance 캐시를 /tmp로 분리해 앱 DB와 충돌 방지
yf.set_tz_cache_location("/tmp/yfinance_cache")


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """
    여러 티커의 현재가를 한 번에 조회합니다.
    KR 6자리 숫자 티커는 자동으로 .KS 접미사를 붙여 조회합니다.
    조회 실패한 티커는 결과에서 제외됩니다.
    """
    if not tickers:
        return {}

    # 원본 ticker → yfinance ticker 매핑 (KR: .KS 추가)
    yf_map = {t: _to_yf_ticker(t) for t in tickers}
    yf_tickers = list(yf_map.values())

    data = yf.download(
        tickers=yf_tickers,
        period="1d",
        interval="1m",
        progress=False,
        auto_adjust=True,
    )

    prices: dict[str, float] = {}

    if len(yf_tickers) == 1:
        orig_ticker = tickers[0]
        if not data.empty:
            close = data["Close"]
            # yfinance 2.x returns a DataFrame even for a single ticker
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
            val = close.dropna()
            if not val.empty:
                prices[orig_ticker] = float(val.iloc[-1])
    else:
        for orig_ticker, yf_ticker in yf_map.items():
            try:
                price = float(data["Close"][yf_ticker].dropna().iloc[-1])
                prices[orig_ticker] = price
            except (KeyError, IndexError):
                pass

    return prices


def fetch_market_data(
    ticker: str,
    market: Literal["KR", "US"],
    currency: str,
    yf_ticker: str | None = None,
) -> MarketData:
    """1년치 일봉 OHLCV를 조회해 기술지표가 포함된 MarketData를 반환합니다.

    Args:
        ticker: 원본 종목코드 (예: 005930, AAPL)
        market: 'KR' | 'US'
        currency: 'KRW' | 'USD'
        yf_ticker: yfinance용 티커 (None이면 market 기준 자동 설정, KR → '{ticker}.KS')
                   KOSDAQ 종목은 호출부에서 '{ticker}.KQ'로 전달할 것.

    Raises:
        ValueError: 조회 결과가 비어 있을 때
    """
    if yf_ticker is None:
        yf_ticker = f"{ticker}.KS" if market == "KR" else ticker

    data = yf.download(
        tickers=yf_ticker,
        period="1y",
        interval="1d",
        progress=False,
        auto_adjust=True,
    )

    if data.empty:
        raise ValueError(f"No price data for {yf_ticker}")

    closes = data["Close"].squeeze()
    highs = data["High"].squeeze()
    lows = data["Low"].squeeze()
    volumes = data["Volume"].squeeze()

    # 30일 고점: KR은 거래일 기준 tail(30), US는 최근 30 캘린더일 날짜 필터
    if market == "KR":
        high_30d = float(highs.tail(30).max())
    else:
        cutoff = closes.index[-1] - pd.Timedelta(days=30)
        high_30d = float(highs[highs.index >= cutoff].max())

    # MACD, 볼린저는 중간 결과를 변수에 저장해 재계산 방지
    macd_line, macd_signal, macd_hist = calc_macd(closes)
    bb_upper, bb_middle, bb_lower = calc_bollinger(closes)

    return MarketData(
        ticker=ticker,
        current_price=float(closes.iloc[-1]),
        currency=currency,
        market=market,
        high_30d=high_30d,
        rsi_14=calc_rsi(closes),
        sma_20=calc_sma(closes, 20),
        sma_60=calc_sma(closes, 60),
        ema_12=calc_ema(closes, 12),
        ema_26=calc_ema(closes, 26),
        macd_line=macd_line,
        macd_signal=macd_signal,
        macd_hist=macd_hist,
        bb_upper=bb_upper,
        bb_middle=bb_middle,
        bb_lower=bb_lower,
        disparity_20=calc_disparity(closes),
        atr_14=calc_atr(highs, lows, closes),
        volume_ratio_20=calc_volume_ratio(volumes),
    )
