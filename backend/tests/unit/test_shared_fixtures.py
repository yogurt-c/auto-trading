"""shared/fixtures/의 입력 → 기대 출력을 현재 도메인·지표 코드가 그대로 재현하는지 확인.

도메인 로직을 바꿨는데 이 테스트가 실패하면, 같은 커밋에서
`cd research && .venv/bin/python scripts/gen_fixtures.py`로 fixture를 재생성한다.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest

from app.domain.trading_strategy.services import EntryGate, OrderSizer, StrategyEvaluator
from app.domain.trading_strategy.value_objects import EvaluationResult, MarketData
from app.infrastructure.indicators import build_market_data

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "shared" / "fixtures"
REL_TOL = 1e-9


def _cases(category: str) -> list:
    paths = sorted((FIXTURES_DIR / category).glob("*.json"))
    return [pytest.param(json.loads(p.read_text(encoding="utf-8")), id=p.stem) for p in paths]


def _assert_close(actual, expected, path: str = "") -> None:
    if isinstance(expected, dict):
        assert set(actual) == set(expected), path
        for key in expected:
            if key in ("note", "blocked_reason"):  # 참고용 문자열
                continue
            _assert_close(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, float) and isinstance(actual, (int, float)):
        assert math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=1e-12), path
    else:
        assert actual == expected, path


def test_fixtures_exist():
    assert all(_cases(c) for c in ("indicators", "evaluator", "gate", "sizer"))


@pytest.mark.parametrize("case", _cases("indicators"))
def test_indicators(case):
    data = case["input"]
    idx = pd.DatetimeIndex(data["dates"])

    def series(key: str) -> pd.Series:
        return pd.Series(data[key], index=idx, dtype=float)

    md = build_market_data(
        "TEST", "KR", "KRW", series("high"), series("low"), series("close"), series("volume")
    )
    _assert_close(md.model_dump(), case["expected"])


@pytest.mark.parametrize("case", _cases("evaluator"))
def test_evaluator(case):
    data = case["input"]
    result = StrategyEvaluator().evaluate(
        data["strategy"], MarketData(**data["market_data"]), data["holding"]
    )
    _assert_close(result.model_dump(), case["expected"])


@pytest.mark.parametrize("case", _cases("gate"))
def test_gate(case):
    data = case["input"]
    evaluation = EvaluationResult(
        ticker="TEST", current_price=100.0, exit_triggered=False, conditions={}, **data["result"]
    )
    decision = EntryGate().apply(data["strategy"], evaluation, data["position_value"])
    _assert_close(decision.model_dump(), case["expected"])


@pytest.mark.parametrize("case", _cases("sizer"))
def test_sizer(case):
    data = case["input"]
    sizer = OrderSizer()
    if "buy" in data:
        assert sizer.buy_qty(**data["buy"]) == case["expected"]
    else:
        assert sizer.sell_qty(**data["sell"]) == case["expected"]
