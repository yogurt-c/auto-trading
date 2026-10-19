"""shared/fixtures/ 생성 — backend 도메인 로직의 입력 → 기대 출력 JSON.

pytest(backend)와 Android Kotlin 테스트가 같은 파일을 읽어 같은 결과를 내는지 확인한다.
입력 시세는 결정적인 합성 데이터만 쓴다 (KRX 원본은 재배포 금지).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from app.domain.trading_strategy.services import EntryGate, OrderSizer, StrategyEvaluator
from app.domain.trading_strategy.value_objects import EvaluationResult, MarketData
from app.infrastructure.indicators import INDICATOR_LOOKBACK_BARS, build_market_data

SCHEMA_VERSION = 1


def _ohlcv(closes: list[float], volumes: list[float]) -> dict[str, list]:
    days = pd.bdate_range("2024-01-02", periods=len(closes))
    return {
        "dates": [f"{d:%Y-%m-%d}" for d in days],
        "high": [round(c * 1.012, 4) for c in closes],
        "low": [round(c * 0.988, 4) for c in closes],
        "close": [round(c, 4) for c in closes],
        "volume": volumes,
    }


def _series(n: int, fn) -> list[float]:
    return [fn(i) for i in range(n)]


def indicator_cases() -> dict[str, dict]:
    """이름 → OHLCV 입력. 길이·추세·결측 경계를 고루 덮는다."""
    flat_vol = [100_000.0] * 300
    return {
        "uptrend_300_bars_truncated_to_lookback": _ohlcv(
            _series(300, lambda i: 50_000 + 120 * i + 900 * math.sin(i / 4)), flat_vol
        ),
        "downtrend_monotonic_rsi_zero": _ohlcv(
            _series(120, lambda i: 80_000 - 250 * i + 400 * math.sin(i / 3)), flat_vol[:120]
        ),
        "zigzag_volume_spike_today": _ohlcv(
            _series(90, lambda i: 30_000 + 1_500 * math.sin(i / 2.5)),
            [100_000.0] * 89 + [350_000.0],
        ),
        "short_40_bars_no_sma60": _ohlcv(
            _series(40, lambda i: 12_000 + 50 * math.cos(i / 2)), flat_vol[:40]
        ),
        "too_short_10_bars": _ohlcv(_series(10, lambda i: 5_000 + 10 * i), flat_vol[:10]),
        "flat_price_rsi_undefined": _ohlcv([20_000.0] * 60, flat_vol[:60]),
    }


def market_data_from_case(case: dict) -> MarketData:
    idx = pd.DatetimeIndex(case["dates"])
    series = {k: pd.Series(case[k], index=idx, dtype=float) for k in ("high", "low", "close")}
    return build_market_data(
        ticker="TEST",
        market="KR",
        currency="KRW",
        highs=series["high"],
        lows=series["low"],
        closes=series["close"],
        volumes=pd.Series(case["volume"], index=idx, dtype=float),
    )


def _md(**kw: Any) -> dict:
    return {"ticker": "TEST", "current_price": 100.0, "market": "KR", "currency": "KRW", **kw}


def evaluator_cases() -> dict[str, dict]:
    """이름 → (strategy, market_data, holding)."""
    rsi_vol = {"entry_rsi_below": 55.0, "entry_volume_surge": 2.0}
    three = {"entry_rsi_below": 30.0, "entry_price_drop_pct": -5.0, "entry_bb_lower_touch": True}
    exits = {"entry_rsi_below": 30.0, "take_profit_pct": 10.0, "stop_loss_pct": -5.0}
    return {
        "price_drop_triggered": ({"entry_price_drop_pct": -5.0}, _md(current_price=94.0, high_30d=100.0), None),
        "price_drop_not_triggered": ({"entry_price_drop_pct": -5.0}, _md(current_price=97.0, high_30d=100.0), None),
        "rsi_boundary_equal_triggers": ({"entry_rsi_below": 30.0}, _md(rsi_14=30.0), None),
        "bb_lower_touch": ({"entry_bb_lower_touch": True}, _md(current_price=95.0, bb_lower=95.0), None),
        "macd_hist_zero_not_positive": ({"entry_macd_hist_positive": True}, _md(macd_hist=0.0), None),
        "disparity_below": ({"entry_disparity_below": -5.0}, _md(disparity_20=-6.2), None),
        "volume_surge_boundary": ({"entry_volume_surge": 2.0}, _md(volume_ratio_20=2.0), None),
        "sma_cross_60_above": ({"entry_sma_cross": 60}, _md(current_price=101.0, sma_60=100.0), None),
        "sma_cross_20_equal_not_above": ({"entry_sma_cross": 20}, _md(sma_20=100.0), None),
        "s0_preset_one_of_two": (rsi_vol, _md(rsi_14=48.0, volume_ratio_20=1.1), None),
        "s0_preset_none": (rsi_vol, _md(rsi_14=61.0, volume_ratio_20=1.1), None),
        "three_conditions_missing_rsi_data": (three, _md(current_price=90.0, high_30d=100.0, bb_lower=85.0), None),
        "take_profit_with_holding": (exits, _md(current_price=111.0, rsi_14=50.0), {"avg_price": 100.0}),
        "stop_loss_with_holding": (exits, _md(current_price=94.0, rsi_14=50.0), {"avg_price": 100.0}),
        "exit_ignored_without_holding": (exits, _md(current_price=50.0, rsi_14=50.0), None),
    }  # fmt: skip


def gate_cases() -> dict[str, dict]:
    def result(triggered: bool, score: float | None) -> dict:
        return {"entry_triggered": triggered, "signal_score": score}

    two = {"entry_rsi_below": 55.0, "entry_volume_surge": 2.0, "max_position": 3_000_000.0}
    three = {**two, "entry_sma_cross": 20}
    return {
        "no_signal": (two, result(False, 0.0), 0.0),
        "two_conditions_half_passes": (two, result(True, 0.5), 0.0),
        "three_conditions_one_third_blocked": (three, result(True, 1 / 3), 0.0),
        "at_max_position_blocked": (two, result(True, 1.0), 3_000_000.0),
        "below_max_position_allowed": (two, result(True, 1.0), 2_999_999.0),
        "no_max_position_single_condition": ({"entry_rsi_below": 30.0}, result(True, 1.0), 1e12),
    }


def sizer_cases() -> dict[str, dict]:
    return {
        "buy_first_tranche": {"buy": [3_000_000, 0, 10_000, 1e9]},
        "buy_capped_by_limit": {"buy": [3_000_000, 2_500_000, 10_000, 1e9]},
        "buy_capped_by_cash": {"buy": [3_000_000, 0, 10_000, 305_000]},
        "buy_price_above_budget": {"buy": [30_000, 0, 20_000, 1e9]},
        "sell_half_rounds_up": {"sell": [3, 0.5]},
        "sell_single_share": {"sell": [1, 0.5]},
        "sell_default_ratio_all": {"sell": [10, None]},
    }


def build_all() -> dict[str, dict[str, dict]]:
    """카테고리 → 파일 이름 → 내용."""
    evaluator, gate, sizer = StrategyEvaluator(), EntryGate(), OrderSizer()
    out: dict[str, dict[str, dict]] = {"indicators": {}, "evaluator": {}, "gate": {}, "sizer": {}}

    for name, case in indicator_cases().items():
        expected = market_data_from_case(case).model_dump()
        out["indicators"][name] = {"input": case, "expected": expected}

    for name, (strategy, md, holding) in evaluator_cases().items():
        result = evaluator.evaluate(strategy, MarketData(**md), holding)
        out["evaluator"][name] = {
            "input": {"strategy": strategy, "market_data": md, "holding": holding},
            "expected": result.model_dump(),
        }

    for name, (strategy, res, position_value) in gate_cases().items():
        evaluation = EvaluationResult(
            ticker="TEST", current_price=100.0, exit_triggered=False, conditions={}, **res
        )
        decision = gate.apply(strategy, evaluation, position_value)
        out["gate"][name] = {
            "input": {"strategy": strategy, "result": res, "position_value": position_value},
            "expected": decision.model_dump(),
        }

    for name, case in sizer_cases().items():
        if "buy" in case:
            max_pos, pos_val, price, cash = case["buy"]
            args = {"max_position": max_pos, "position_value": pos_val, "price": price}
            qty = sizer.buy_qty(**args, available_cash=cash)
            out["sizer"][name] = {
                "input": {"buy": {**args, "available_cash": cash}},
                "expected": qty,
            }
        else:
            shares, ratio = case["sell"]
            qty = sizer.sell_qty(shares, ratio)
            out["sizer"][name] = {
                "input": {"sell": {"shares": shares, "sell_ratio": ratio}},
                "expected": qty,
            }
    return out


def render(content: dict) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "lookback_bars": INDICATOR_LOOKBACK_BARS,
        **content,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_all(root: Path) -> list[Path]:
    written = []
    for category, files in build_all().items():
        for name, content in files.items():
            path = root / category / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render(content), encoding="utf-8")
            written.append(path)
    return written
