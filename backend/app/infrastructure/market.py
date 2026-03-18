"""실시간 시세 조회 (Yahoo Finance)."""

from __future__ import annotations

import yfinance as yf

# yfinance 캐시를 /tmp로 분리해 앱 DB와 충돌 방지
yf.set_tz_cache_location("/tmp/yfinance_cache")


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """
    여러 티커의 현재가를 한 번에 조회합니다.
    조회 실패한 티커는 결과에서 제외됩니다.
    """
    if not tickers:
        return {}

    data = yf.download(
        tickers=tickers,
        period="1d",
        interval="1m",
        progress=False,
        auto_adjust=True,
    )

    prices: dict[str, float] = {}

    if len(tickers) == 1:
        ticker = tickers[0]
        if not data.empty:
            prices[ticker] = float(data["Close"].iloc[-1])
    else:
        for ticker in tickers:
            try:
                price = float(data["Close"][ticker].dropna().iloc[-1])
                prices[ticker] = price
            except (KeyError, IndexError):
                pass

    return prices
