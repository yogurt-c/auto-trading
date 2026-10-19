"""종목·일자별 MarketData 사전 계산.

MarketData는 전략 파라미터와 무관하므로 한 번 계산해 parquet로 저장하고, 파라미터 조합마다
StrategyEvaluator만 다시 돌린다. 계산은 backend의 build_market_data를 그대로 호출한다.
"""

from __future__ import annotations

import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from app.domain.trading_strategy.value_objects import MarketData
from app.infrastructure.indicators import INDICATOR_LOOKBACK_BARS, build_market_data

_PRICE_COLUMNS = ["open", "high", "low", "close"]


def compute_for_code(code_rows: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    """한 종목의 start~end 각 거래일에 대해 MarketData 필드 dict를 만든다.

    판단일 t의 입력: t까지 거래된(종가 있는) 일봉 중 마지막 INDICATOR_LOOKBACK_BARS개를
    t 기준 수정주가로 환산 — t 이후의 분할·권리락은 반영하지 않는다.
    """
    rows = code_rows[code_rows["close"].notna()].sort_values("date").reset_index(drop=True)
    adjusted = rows[_PRICE_COLUMNS].mul(rows["adj_ratio"], axis=0)
    adj_volume = rows["volume"] / rows["adj_ratio"]
    dates = pd.DatetimeIndex(rows["date"])
    code = str(rows["code"].iloc[0]) if len(rows) else ""

    out: list[dict] = []
    for i in range(len(rows)):
        day = dates[i]
        if not (start <= day <= end):
            continue
        lo = max(0, i + 1 - INDICATOR_LOOKBACK_BARS)
        scale = rows["adj_ratio"].iloc[i]
        idx = dates[lo : i + 1]
        md = build_market_data(
            ticker=code,
            market="KR",
            currency="KRW",
            highs=pd.Series(adjusted["high"].iloc[lo : i + 1].to_numpy() / scale, index=idx),
            lows=pd.Series(adjusted["low"].iloc[lo : i + 1].to_numpy() / scale, index=idx),
            closes=pd.Series(adjusted["close"].iloc[lo : i + 1].to_numpy() / scale, index=idx),
            volumes=pd.Series(adj_volume.iloc[lo : i + 1].to_numpy() * scale, index=idx),
        )
        out.append({"date": day, **md.model_dump()})
    return out


def _worker(args: tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]) -> list[dict]:
    return compute_for_code(*args)


def precompute(
    panel: pd.DataFrame,
    codes: list[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    path: Path,
    workers: int | None = None,
) -> pd.DataFrame:
    """codes 전체의 MarketData 표를 만들어 path에 저장한다 (있으면 읽기만)."""
    if path.exists():
        return pd.read_parquet(path)
    subset = panel[panel["code"].isin(codes)]
    jobs = [(rows, start, end) for _, rows in subset.groupby("code")]
    logger.info(f"MarketData 사전 계산: {len(jobs)}개 종목")
    with ProcessPoolExecutor(max_workers=workers) as pool:
        records = [r for chunk in pool.map(_worker, jobs, chunksize=1) for r in chunk]
    table = pd.DataFrame(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_parquet(path, index=False)
    return table


def to_market_data(row: dict) -> MarketData:
    """parquet 행 → MarketData. NaN은 None으로 되돌린다."""
    clean = {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in row.items()
        if k != "date"
    }
    return MarketData(**clean)


# StrategyEvaluator가 읽는 MarketData 필드 — 메모리를 줄이려고 이것만 보관한다
EVALUATOR_FIELDS = (
    "current_price",
    "high_30d",
    "rsi_14",
    "sma_20",
    "sma_60",
    "macd_hist",
    "bb_lower",
    "disparity_20",
    "volume_ratio_20",
)


class MarketDataStore:
    """(code, date) → MarketData 필드 dict. 종목별 numpy 배열로 보관 (수십만 행)."""

    def __init__(self, table: pd.DataFrame) -> None:
        self._rows: dict[str, tuple[dict[pd.Timestamp, int], np.ndarray]] = {}
        for code, rows in table.groupby("ticker"):
            dates = pd.DatetimeIndex(rows["date"])
            values = rows[list(EVALUATOR_FIELDS)].to_numpy(dtype=float)
            self._rows[str(code)] = ({d: i for i, d in enumerate(dates)}, values)

    def get(self, key: tuple[str, pd.Timestamp], default: dict | None = None) -> dict | None:
        code, day = key
        entry = self._rows.get(code)
        if entry is None:
            return default
        index, values = entry
        i = index.get(day)
        if i is None:
            return default
        return {"ticker": code, **dict(zip(EVALUATOR_FIELDS, values[i].tolist(), strict=True))}
