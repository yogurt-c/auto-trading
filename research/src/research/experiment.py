"""사전 등록 기준(config/criteria.yaml)에 따른 단계별 실험.

학습 구간에서 S0 → S1(국면) → S2(공시)를 하나씩 붙여 채택 여부를 정하고, 튜닝 계열과 비교해
최종 후보 1개를 고른다. 검증 구간은 최종 후보로 한 번만 돌린다.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from loguru import logger

from research import config
from research.baselines import buy_and_hold, monthly_dca
from research.costs import CostModel
from research.engine import (
    BacktestResult,
    Engine,
    EngineConfig,
    EqualWeightSpec,
    MarketInputs,
    StrategySpec,
)
from research.metrics import (
    daily_returns,
    deflated_sharpe,
    max_drawdown,
    money_weighted_return,
    prob_sharpe_greater,
    sharpe,
    summary,
    yearly_sharpe,
)

FORWARD_DAYS = 20


@dataclass(frozen=True)
class Period:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp

    @classmethod
    def load(cls, name: str) -> Period:
        p = config.load("periods")[name]
        return cls(name, pd.Timestamp(p["start"]), pd.Timestamp(p["end"]))


class Lab:
    """엔진·비용·기준 전략을 묶어 기간별 실행을 담당한다."""

    def __init__(self, inputs: MarketInputs, etf: pd.DataFrame, slippage: float | None = None):
        costs_cfg = config.load("costs")
        strategy_cfg = config.load("strategy")
        self.inputs = inputs
        self.etf = etf
        self.costs = CostModel.from_config(costs_cfg)
        if slippage is not None:
            self.costs = self.costs.with_slippage(slippage)
        self.etf_costs = CostModel.from_config(costs_cfg, etf=True)
        self.engine_config = EngineConfig(
            capital=strategy_cfg["capital"],
            max_position_pct=strategy_cfg["max_position_pct_of_equity"],
            dividend_tax_rate=costs_cfg["dividend_tax_rate"],
        )
        self._engine = Engine(inputs, self.engine_config, self.costs)

    def run(self, spec: StrategySpec | EqualWeightSpec, period: Period) -> BacktestResult:
        logger.info(f"[{period.name}] {spec.name}")
        return self._engine.run(spec, period.start, period.end)

    def benchmarks(self, period: Period) -> dict[str, pd.Series]:
        etf = self.etf.loc[period.start : period.end]
        capital = self.engine_config.capital
        b2, _ = monthly_dca(etf, capital, self.etf_costs)
        return {
            "B1": buy_and_hold(etf, capital, self.etf_costs),
            "B2": b2,
            "B3": self.run(EqualWeightSpec(), period).equity,
        }

    def b2_money_weighted(self, period: Period) -> float:
        etf = self.etf.loc[period.start : period.end]
        equity, flows = monthly_dca(etf, self.engine_config.capital, self.etf_costs)
        return money_weighted_return(flows, float(equity.iloc[-1]), equity.index[-1])


def layer_adopted(base: BacktestResult, layered: BacktestResult) -> tuple[bool, dict]:
    """필터 채택: 학습 Sharpe +0.10 이상 개선 & 8개 연도 중 5개 이상 연간 Sharpe 개선."""
    rule = config.load("criteria")["layer_adoption"]
    base_r, layer_r = daily_returns(base.equity), daily_returns(layered.equity)
    gain = sharpe(layer_r) - sharpe(base_r)
    years_improved = int((yearly_sharpe(layer_r) > yearly_sharpe(base_r)).sum())
    adopted = gain >= rule["min_sharpe_gain"] and years_improved >= rule["min_years_improved"]
    return adopted, {"sharpe_gain": gain, "years_improved": years_improved}


def forward_returns(
    inputs: MarketInputs, events: list[tuple[pd.Timestamp, str]], days: int = FORWARD_DAYS
) -> list[float]:
    """판단일 t의 이벤트 → t+1 시가 대비 t+days 종가 수익률 (분할 조정)."""
    # adj_ratio_t = t 이후(t 제외) 조정 계수의 곱
    adj_ratio = inputs.factors[::-1].cumprod()[::-1].shift(-1, fill_value=1.0)
    adj_close = inputs.closes * adj_ratio
    adj_open = inputs.opens * adj_ratio
    trading_days = inputs.trading_days
    out = []
    for day, code in events:
        i = trading_days.get_loc(day)
        if i + days >= len(trading_days):
            continue
        entry = adj_open.at[trading_days[i + 1], code]
        exit_ = adj_close.at[trading_days[i + days], code]
        if pd.notna(entry) and pd.notna(exit_) and entry > 0:
            out.append(float(exit_ / entry - 1))
    return out


def veto_decision(inputs: MarketInputs, layered: BacktestResult) -> tuple[bool, dict]:
    """공시 거부권 구현 여부: 막은 진입 수와 막힌 진입의 이후 수익률 격차."""
    rule = config.load("criteria")["layer_adoption"]["disclosure_veto_implement_if"]
    blocked = forward_returns(inputs, layered.blocked_by_veto)
    trading_days = inputs.trading_days
    entries = [  # 체결일 전날이 판단일
        (trading_days[trading_days.get_loc(f.date) - 1], f.code)
        for f in layered.fills
        if f.side == "buy" and f.reason == "entry"
    ]
    taken = forward_returns(inputs, entries)
    gap = (np.mean(taken) - np.mean(blocked)) * 100 if blocked and taken else float("nan")
    implement = len(layered.blocked_by_veto) >= rule["min_blocked_entries_train"] and (
        gap >= rule["min_forward_return_gap_pct"]
    )
    return implement, {
        "blocked_entries": len(layered.blocked_by_veto),
        "blocked_mean_fwd_pct": float(np.mean(blocked) * 100) if blocked else None,
        "taken_mean_fwd_pct": float(np.mean(taken) * 100) if taken else None,
        "gap_pct": None if np.isnan(gap) else float(gap),
    }


def tuning_specs(base: StrategySpec) -> list[StrategySpec]:
    grid = config.load("strategy")["tuning_grid"]
    keys = list(grid)
    specs = []
    for values in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, values, strict=True))
        name = "tuned_" + "_".join(f"{k.split('_')[-2]}{v}" for k, v in params.items())
        specs.append(replace(base, name=name, params=params))
    return specs


def neighbor_drop(best: StrategySpec, trial_sharpes: dict[str, float], specs: list) -> float:
    """각 파라미터를 격자에서 ±1단계 바꾼 이웃 중 최대 Sharpe 하락률."""
    grid = config.load("strategy")["tuning_grid"]
    by_params = {tuple(sorted(s.params.items())): trial_sharpes[s.name] for s in specs}
    base_sharpe = trial_sharpes[best.name]
    worst = 0.0
    for key, values in grid.items():
        i = values.index(best.params[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(values):
                neighbor = tuple(sorted({**best.params, key: values[j]}.items()))
                drop = (base_sharpe - by_params[neighbor]) / abs(base_sharpe) if base_sharpe else 0
                worst = max(worst, drop)
    return worst


def check_test(
    final: BacktestResult,
    stressed: BacktestResult,
    benches: dict[str, pd.Series],
    train_sharpe: float,
    train_report: dict,
) -> dict:
    """검증 구간 통과 기준 P1–P7."""
    rules = {r["id"]: r for r in config.load("criteria")["test_pass"]}
    crit = config.load("criteria")["metrics"]["bootstrap"]
    r = daily_returns(final.equity)
    comp_name = max(("B1", "B3"), key=lambda k: sharpe(daily_returns(benches[k])))
    comp_r = daily_returns(benches[comp_name])
    s, s_comp = sharpe(r), sharpe(comp_r)
    mdd_excess = (max_drawdown(benches["B1"]) - max_drawdown(final.equity)) * 100
    prob = prob_sharpe_greater(
        r, comp_r, reps=crit["reps"], mean_block=crit["mean_block_days"], seed=crit["seed"]
    )
    checks = {
        "P1": {"pass": s > s_comp, "sharpe": s, "comparator": comp_name, "comp_sharpe": s_comp},
        "P2": {
            "pass": mdd_excess <= rules["P2"]["max_mdd_excess_pct"],
            "mdd_excess_pct": mdd_excess,
        },
        "P3": {"pass": prob >= rules["P3"]["min_probability"], "probability": prob},
        "P4": {"pass": s >= train_sharpe * rules["P4"]["min_ratio"], "train_sharpe": train_sharpe},
        "P5": {
            "pass": sharpe(daily_returns(stressed.equity)) > s_comp,
            "stressed_sharpe": sharpe(daily_returns(stressed.equity)),
        },
        "P6": {"pass": final.entries >= rules["P6"]["min_entries"], "entries": final.entries},
    }
    if train_report["final"]["family"] == "tuned":
        p7 = train_report["final"]["p7"]
        checks["P7"] = {
            "pass": p7["deflated_sharpe"] >= rules["P7"]["min_deflated_sharpe"]
            and p7["neighbor_drop"] <= rules["P7"]["max_neighbor_drop"],
            **p7,
        }
    checks["passed"] = all(c["pass"] for c in checks.values())
    return checks


def describe(equity: pd.Series, result: BacktestResult | None = None) -> dict:
    out = summary(equity)
    if result is not None:
        out["entries"] = result.entries
        out["dividends"] = result.dividends
    return out


def deflated_for(final: BacktestResult, trial_sharpes: list[float]) -> float:
    return deflated_sharpe(daily_returns(final.equity), trial_sharpes)
