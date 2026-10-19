"""학습 단계 → 최종 후보 선택 → 검증 단계 (사전 등록 기준 그대로)."""

from __future__ import annotations

from dataclasses import asdict

from loguru import logger

from research import config
from research.engine import BacktestResult, StrategySpec
from research.experiment import (
    Lab,
    Period,
    check_test,
    deflated_for,
    describe,
    layer_adopted,
    neighbor_drop,
    tuning_specs,
    veto_decision,
)
from research.metrics import daily_returns, sharpe


def _sharpe(result: BacktestResult) -> float:
    return sharpe(daily_returns(result.equity))


def run_train(lab: Lab) -> dict:
    period = Period.load("train")
    strategy_cfg = config.load("strategy")
    benches = lab.benchmarks(period)
    comparator = max(("B1", "B3"), key=lambda k: sharpe(daily_returns(benches[k])))
    report: dict = {"benchmarks": {k: describe(v) for k, v in benches.items()}}
    report["comparator"] = comparator

    s0 = StrategySpec("S0", strategy_cfg["s0_preset"])
    chain = lab.run(s0, period)
    report["S0"] = describe(chain.equity, chain)

    s1 = lab.run(StrategySpec("S1_regime", s0.params, use_regime_filter=True), period)
    adopted, detail = layer_adopted(chain, s1)
    report["S1_regime"] = {**describe(s1.equity, s1), **detail, "adopted": adopted}
    if adopted:
        chain = s1

    s2_spec = StrategySpec(
        "S2_veto", s0.params, chain.spec.use_regime_filter, use_disclosure_veto=True
    )
    s2 = lab.run(s2_spec, period)
    implement, veto_detail = veto_decision(lab.inputs, s2)
    adopted, detail = layer_adopted(chain, s2)
    report["S2_veto"] = {
        **describe(s2.equity, s2),
        **detail,
        **veto_detail,
        "implement": implement,
        "adopted": implement and adopted,
    }
    if implement and adopted:
        chain = s2

    report["db_presets"] = {
        code: describe(r.equity, r)
        for code, params in strategy_cfg["db_presets"].items()
        for r in [lab.run(StrategySpec(f"db_{code}", params), period)]
    }

    tuned, trial_sharpes, specs = _run_tuning(lab, chain.spec, period)
    report["tuning"] = {"trials": len(trial_sharpes), "best": tuned.spec.name}
    report["final"] = _pick_final(chain, tuned, trial_sharpes, specs)
    final_sharpe = report["final"]["train_sharpe"]
    report["train_gate"] = {
        "pass": final_sharpe > sharpe(daily_returns(benches[comparator])),
        "final_sharpe": final_sharpe,
        "comparator_sharpe": sharpe(daily_returns(benches[comparator])),
    }
    return report


def _run_tuning(
    lab: Lab, base: StrategySpec, period: Period
) -> tuple[BacktestResult, dict[str, float], list[StrategySpec]]:
    specs = tuning_specs(base)
    results = {s.name: lab.run(s, period) for s in specs}
    trial_sharpes = {name: _sharpe(r) for name, r in results.items()}
    best_name = max(trial_sharpes, key=trial_sharpes.get)
    return results[best_name], trial_sharpes, specs


def _pick_final(
    chain: BacktestResult,
    tuned: BacktestResult,
    trial_sharpes: dict[str, float],
    specs: list[StrategySpec],
) -> dict:
    """학습 Sharpe가 높은 쪽. 튜닝 계열이면 P7 판정값(DSR, 이웃 하락률)을 함께 남긴다."""
    chain_sharpe, tuned_sharpe = _sharpe(chain), _sharpe(tuned)
    if chain_sharpe >= tuned_sharpe:
        return {"family": "preset", "spec": asdict(chain.spec), "train_sharpe": chain_sharpe}
    all_trials = [*trial_sharpes.values(), chain_sharpe]
    p7 = {
        "deflated_sharpe": deflated_for(tuned, all_trials),
        "neighbor_drop": neighbor_drop(tuned.spec, trial_sharpes, specs),
    }
    logger.info(f"튜닝 계열 선택: {tuned.spec.name} (P7 {p7})")
    return {"family": "tuned", "spec": asdict(tuned.spec), "train_sharpe": tuned_sharpe, "p7": p7}


def run_test(lab: Lab, stressed_lab: Lab, train_report: dict) -> dict:
    period = Period.load("test")
    spec = StrategySpec(**train_report["final"]["spec"])
    final = lab.run(spec, period)
    stressed = stressed_lab.run(spec, period)
    benches = lab.benchmarks(period)
    checks = check_test(
        final, stressed, benches, train_report["final"]["train_sharpe"], train_report
    )
    return {
        "spec": train_report["final"]["spec"],
        "strategy": describe(final.equity, final),
        "stressed": describe(stressed.equity, stressed),
        "benchmarks": {k: describe(v) for k, v in benches.items()},
        "b2_money_weighted": lab.b2_money_weighted(period),
        "checks": checks,
        "decision": "adopt_strategy" if checks["passed"] else "fallback_index_dca",
        "equity": {"strategy": final.equity, **benches},
    }
