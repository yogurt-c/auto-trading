"""수집한 데이터(research/data/) → 엔진 입력(MarketInputs)."""

from __future__ import annotations

import json

import pandas as pd

from research import config
from research.engine import MarketInputs
from research.market_data import MarketDataStore, precompute
from research.paths import DATA_DIR

PANEL_PATH = DATA_DIR / "panel.parquet"
UNIVERSE_PATH = DATA_DIR / "universe.parquet"
INDEX_PATH = DATA_DIR / "kospi200.parquet"
MARKET_DATA_PATH = DATA_DIR / "market_data.parquet"
DART_DIR = DATA_DIR / "dart"


def regime_series(index_closes: pd.Series, sma_period: int) -> pd.Series:
    """지수 종가 > SMA(period) 여부. SMA를 계산할 수 없는 초기 구간은 False."""
    sma = index_closes.rolling(sma_period).mean()
    return (index_closes > sma) & sma.notna()


def veto_windows(
    disclosures: pd.DataFrame,
    trading_days: pd.DatetimeIndex,
    keywords: list[str],
    block_days: int,
) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """악재 공시 → 진입 금지 구간. 접수일 다음 거래일부터 block_days 거래일."""
    if disclosures.empty:
        return []
    pattern = "|".join(keywords)
    hits = disclosures[disclosures["report_nm"].str.contains(pattern, regex=True, na=False)]
    windows = []
    for rcept_dt in pd.to_datetime(hits["rcept_dt"], format="%Y%m%d"):
        start = trading_days.searchsorted(rcept_dt, side="right")
        if start >= len(trading_days):
            continue
        end = min(start + block_days - 1, len(trading_days) - 1)
        windows.append((trading_days[start], trading_days[end]))
    return windows


def _load_dart(trading_days: pd.DatetimeIndex) -> tuple[dict, dict]:
    code_map_path = DART_DIR / "code_map.parquet"
    if not code_map_path.exists():
        return {}, {}
    code_map = pd.read_parquet(code_map_path)["corp_code"].to_dict()
    veto_cfg = config.load("strategy")["disclosure_veto"]
    keywords = veto_cfg["report_name_keywords"] + veto_cfg["audit_opinion_keywords"]

    veto: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]] = {}
    dividends: dict[tuple[str, int], float] = {}
    for code, corp_code in code_map.items():
        files = list((DART_DIR / "disclosures").glob(f"{corp_code}_*.parquet"))
        if files:
            disclosures = pd.read_parquet(files[0])
            veto[code] = veto_windows(
                disclosures, trading_days, keywords, veto_cfg["block_trading_days"]
            )
        div_path = DART_DIR / "dividends" / f"{corp_code}.json"
        if div_path.exists():
            for year, dps in json.loads(div_path.read_text()).items():
                if dps:
                    dividends[(code, int(year))] = float(dps)
    return veto, dividends


def load_inputs() -> MarketInputs:
    """패널·유니버스·지수·DART를 읽고 MarketData를 (없으면) 사전 계산한다."""
    periods = config.load("periods")
    strategy_cfg = config.load("strategy")
    panel = pd.read_parquet(PANEL_PATH)
    universe = pd.read_parquet(UNIVERSE_PATH)
    codes = sorted(universe["code"].unique())
    panel = panel[panel["code"].isin(codes)]

    table = precompute(
        panel,
        codes,
        pd.Timestamp(periods["train"]["start"]),
        pd.Timestamp(periods["test"]["end"]),
        MARKET_DATA_PATH,
    )

    closes = panel.pivot(index="date", columns="code", values="close")
    trading_days = closes.index
    index_closes = pd.read_parquet(INDEX_PATH)["close"]
    regime = regime_series(index_closes, strategy_cfg["regime_filter"]["sma_period"])
    veto, dividends = _load_dart(trading_days)
    last_trade = panel[panel["close"].notna()].groupby("code")["date"].max().to_dict()

    return MarketInputs(
        opens=panel.pivot(index="date", columns="code", values="open"),
        closes=closes,
        factors=panel.pivot(index="date", columns="code", values="factor").fillna(1.0),
        market_data=MarketDataStore(table),
        universe=universe,
        regime_ok=regime.reindex(trading_days, fill_value=False),
        veto_until=veto,
        dividends=dividends,
        last_trade_date=last_trade,
    )
