"""R2 후보 전략 4개 — 사전 등록(config/r2_strategies.yaml · r2_criteria.yaml) 그대로 실행.

A 레버리지+추세, B 듀얼 모멘텀, D 변동성 돌파는 ETF 비중 교체(rotation.py),
C 단기 모멘텀은 종목 단위 체결·분할·상장폐지가 필요해 engine.Engine(MomentumSpec)으로 돌린다.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from loguru import logger

from research import config
from research.baselines import buy_and_hold
from research.costs import CostModel
from research.data.assets import fetch_yf, load_assets, us_signal_series
from research.engine import Engine, EngineConfig, MarketInputs, MomentumSpec
from research.experiment import Period
from research.inputs import INDEX_PATH, PANEL_PATH, _load_dart
from research.metrics import (
    daily_returns,
    deflated_sharpe,
    prob_sharpe_greater,
    sharpe,
    summary,
)
from research.rotation import AssetCosts, RotationResult, run_breakout, run_rotation
from research.universe import build_universe

CANDIDATES = ("A_leverage_trend", "B_dual_momentum", "C_short_momentum", "D_volatility_breakout")


def month_end_days(days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(days, index=days)
    return pd.DatetimeIndex(s.groupby(days.to_period("M")).max())


# --- 목표 비중 생성 (판단일 → {자산: 비중}) -------------------------------------


def above_sma(closes: pd.Series, sma_days: int) -> pd.Series:
    """종가 > SMA. SMA를 계산할 수 없는 초기 구간은 False."""
    sma = closes.rolling(sma_days).mean()
    return (closes > sma) & sma.notna()


def trend_targets(
    sleeves: list[dict],
    risk_on: dict[str, pd.Series],
    days: pd.DatetimeIndex,
) -> dict[pd.Timestamp, dict[str, float]]:
    """슬리브마다 신호 지수가 SMA 위(risk_on[지수] True)면 risk_on 자산, 아니면 risk_off 자산.

    판단일: 기간 첫날, 매월 마지막 거래일, 어느 슬리브든 상태가 바뀐 날.
    """
    states = pd.DataFrame(
        {i: risk_on[s["signal_index"]].reindex(days) for i, s in enumerate(sleeves)}
    ).astype(bool)
    changed = (states != states.shift(1)).any(axis=1)
    decision_days = set(days[changed.to_numpy()]) | set(month_end_days(days)) | {days[0]}
    targets = {}
    for day in sorted(decision_days):
        weights: dict[str, float] = {}
        for i, sleeve in enumerate(sleeves):
            asset = sleeve["risk_on"] if states.at[day, i] else sleeve["risk_off"]
            weights[asset] = weights.get(asset, 0.0) + sleeve["weight"]
        targets[day] = weights
    return targets


def dual_momentum_targets(
    prices: dict[str, pd.DataFrame],
    risky: list[str],
    safe: str,
    lookback: int,
    days: pd.DatetimeIndex,
) -> dict[pd.Timestamp, dict[str, float]]:
    """매월 말: 위험자산 중 lookback 수익률 최고가 채권보다 높으면 그 자산, 아니면 채권."""
    rets = {a: prices[a]["close"] / prices[a]["close"].shift(lookback) - 1 for a in [*risky, safe]}
    targets = {}
    for day in sorted(set(month_end_days(days)) | {days[0]}):
        best = max(risky, key=lambda a: rets[a].at[day])
        pick = best if rets[best].at[day] > rets[safe].at[day] else safe
        targets[day] = {pick: 1.0}
    return targets


def fixed_mix_targets(
    weights: dict[str, float], days: pd.DatetimeIndex
) -> dict[pd.Timestamp, dict[str, float]]:
    """B4: 기간 첫날과 매월 말에 고정 비중으로 리밸런싱."""
    return {day: dict(weights) for day in sorted(set(month_end_days(days)) | {days[0]})}


# --- 입력 --------------------------------------------------------------------


@dataclass
class R2Inputs:
    calendar: pd.DatetimeIndex
    prices: dict[str, pd.DataFrame]
    risk_on: dict[str, pd.Series]  # 신호 지수 → 한국 거래일별 'SMA 위' 여부
    momentum_inputs: MarketInputs


def load_r2_inputs() -> R2Inputs:
    cfg = config.load("r2_strategies")
    periods = config.load("periods")
    end = periods["test"]["end"]
    end_exclusive = str((pd.Timestamp(end) + pd.Timedelta(days=1)).date())
    kospi200 = pd.read_parquet(INDEX_PATH)["close"]
    calendar = pd.DatetimeIndex(kospi200.index)
    prices = load_assets(cfg, calendar, "2009-01-01", end_exclusive)
    sma_days = cfg["candidates"]["A_leverage_trend"]["sma_days"]
    gspc = fetch_yf("^GSPC", "2009-01-01", end_exclusive)["close"]
    # 미국 지수 SMA는 미국 거래일로 계산하고, 한국 거래일 d에는 d 이전 마지막 미국 종가 기준 값
    us_above = us_signal_series(above_sma(gspc, sma_days).astype(float), calendar) > 0
    risk_on = {"코스피 200": above_sma(kospi200, sma_days), "^GSPC": us_above}
    top_n = cfg["candidates"]["C_short_momentum"]["universe_top_n"]
    return R2Inputs(calendar, prices, risk_on, _momentum_inputs(top_n))


def _momentum_inputs(top_n: int) -> MarketInputs:
    panel = pd.read_parquet(PANEL_PATH)
    universe = build_universe(panel, {**config.load("universe"), "top_n_by_market_cap": top_n})
    panel = panel[panel["code"].isin(set(universe["code"]))]
    closes = panel.pivot(index="date", columns="code", values="close")
    _, dividends = _load_dart(closes.index)
    return MarketInputs(
        opens=panel.pivot(index="date", columns="code", values="open"),
        closes=closes,
        factors=panel.pivot(index="date", columns="code", values="factor").fillna(1.0),
        market_data={},
        universe=universe,
        regime_ok=pd.Series(dtype=bool),
        veto_until={},
        # DART 배당은 시총 상위 50 이력 종목만 있다 — 51~100위 배당 누락 (전략에 불리한 방향)
        dividends=dividends,
        last_trade_date=panel[panel["close"].notna()].groupby("code")["date"].max().to_dict(),
    )


# --- 실행 --------------------------------------------------------------------


class R2Lab:
    def __init__(self, inputs: R2Inputs, slippage_multiplier: float = 1.0) -> None:
        self.inputs = inputs
        self.cfg = config.load("r2_strategies")
        costs_cfg = config.load("costs")
        strategy_cfg = config.load("strategy")
        self.capital = strategy_cfg["capital"]
        commission = costs_cfg["commission_rate"]
        etf_slip = costs_cfg["etf_slippage_rate"] * slippage_multiplier
        gain_tax = self.cfg["overseas_gain_tax_rate"]
        self.asset_costs = {
            name: AssetCosts(commission, etf_slip, gain_tax if spec["tax"] == "gains" else 0.0)
            for name, spec in self.cfg["assets"].items()
        }
        self.breakout_costs = AssetCosts(
            commission, self.cfg["breakout_slippage_rate"] * slippage_multiplier
        )
        self.etf_cost_model = CostModel.from_config(costs_cfg, etf=True).with_slippage(etf_slip)
        stock_costs = CostModel.from_config(costs_cfg)
        self.stock_engine = Engine(
            inputs.momentum_inputs,
            EngineConfig(
                capital=self.capital,
                max_position_pct=1.0,
                dividend_tax_rate=costs_cfg["dividend_tax_rate"],
            ),
            stock_costs.with_slippage(stock_costs.slippage_rate * slippage_multiplier),
        )

    def days(self, period: Period) -> pd.DatetimeIndex:
        cal = self.inputs.calendar
        return cal[(cal >= period.start) & (cal <= period.end)]

    def benchmarks(self, period: Period) -> dict[str, pd.Series]:
        days = self.days(period)
        kr = self.inputs.prices["kr_1x"].loc[days]
        b4 = run_rotation(
            "B4",
            self.inputs.prices,
            fixed_mix_targets({"kr_1x": 0.5, "us_1x": 0.5}, days),
            days,
            self.capital,
            self.asset_costs,
        )
        return {"B1": buy_and_hold(kr, self.capital, self.etf_cost_model), "B4": b4.equity}

    def run(self, name: str, period: Period) -> RotationResult:
        logger.info(f"[{period.name}] {name}")
        c = self.cfg["candidates"][name]
        days = self.days(period)
        prices = self.inputs.prices
        if name == "A_leverage_trend":
            targets = trend_targets(c["sleeves"], self.inputs.risk_on, days)
            return run_rotation(name, prices, targets, days, self.capital, self.asset_costs)
        if name == "B_dual_momentum":
            targets = dual_momentum_targets(prices, c["risky"], c["safe"], c["lookback_days"], days)
            return run_rotation(name, prices, targets, days, self.capital, self.asset_costs)
        if name == "C_short_momentum":
            spec = MomentumSpec(name, c["lookback_days"], c["hold"], c["rebalance_every_days"])
            result = self.stock_engine.run(spec, period.start, period.end)
            return RotationResult(name, result.equity, len(result.fills), 0.0)
        if name == "D_volatility_breakout":
            return run_breakout(
                name, prices[c["asset"]], days, self.capital, self.breakout_costs, c["k"]
            )
        raise ValueError(name)


# --- 판정 --------------------------------------------------------------------


def describe(equity: pd.Series) -> dict:
    out = summary(equity)
    monthly = equity.resample("ME").last().pct_change().dropna()
    out["monthly_mean"] = float(monthly.mean())
    out["monthly_median"] = float(monthly.median())
    out["worst_month"] = float(monthly.min())
    return out


def comparator_of(benches: dict[str, pd.Series]) -> str:
    return max(benches, key=lambda k: sharpe(daily_returns(benches[k])))


def run_r2_train(lab: R2Lab) -> dict:
    period = Period.load("train")
    benches = lab.benchmarks(period)
    comp = comparator_of(benches)
    comp_stats = describe(benches[comp])
    report: dict = {
        "benchmarks": {k: describe(v) for k, v in benches.items()},
        "comparator": comp,
        "candidates": {},
    }
    results = {name: lab.run(name, period) for name in CANDIDATES}
    trial_sharpes = [sharpe(daily_returns(r.equity)) for r in results.values()]
    for name, r in results.items():
        stats = describe(r.equity)
        t1 = stats["sharpe"] > comp_stats["sharpe"]
        t2 = stats["cagr"] > comp_stats["cagr"]
        report["candidates"][name] = {
            **stats,
            "trades": r.trades,
            "taxes": r.taxes,
            "T1": t1,
            "T2": t2,
            "gate": t1 and t2,
            "deflated_sharpe": deflated_sharpe(daily_returns(r.equity), trial_sharpes),
        }
    passing = [n for n, c in report["candidates"].items() if c["gate"]]
    report["final"] = (
        max(passing, key=lambda n: report["candidates"][n]["sharpe"]) if passing else None
    )
    curves = {**benches, **{n: r.equity for n, r in results.items()}}
    report["yearly"] = _yearly(curves)
    report["equity"] = curves
    return report


def _yearly(curves: dict[str, pd.Series]) -> dict[str, dict[int, float]]:
    """연도별 수익률 (첫해는 기간 시작 대비)."""
    out = {}
    for name, eq in curves.items():
        ends = eq.groupby(eq.index.year).last()
        prev = ends.shift(1).fillna(eq.iloc[0])
        out[name] = {int(y): float(v) for y, v in (ends / prev - 1).items()}
    return out


def run_r2_test(lab: R2Lab, stressed: R2Lab, train_report: dict) -> dict:
    period = Period.load("test")
    rules = {r["id"]: r for r in config.load("r2_criteria")["test_pass"]}
    boot = config.load("criteria")["metrics"]["bootstrap"]
    name = train_report["final"]
    final = lab.run(name, period)
    stressed_result = stressed.run(name, period)
    benches = lab.benchmarks(period)
    comp = comparator_of(benches)
    s, comp_s = describe(final.equity), describe(benches[comp])
    prob = prob_sharpe_greater(
        daily_returns(final.equity),
        daily_returns(benches[comp]),
        reps=boot["reps"],
        mean_block=boot["mean_block_days"],
        seed=boot["seed"],
    )
    train_c = train_report["candidates"][name]
    stressed_sharpe = sharpe(daily_returns(stressed_result.equity))
    checks = {
        "P1": {
            "pass": s["sharpe"] > comp_s["sharpe"],
            "sharpe": s["sharpe"],
            "comp": comp_s["sharpe"],
        },
        "P2": {"pass": s["cagr"] > comp_s["cagr"], "cagr": s["cagr"], "comp": comp_s["cagr"]},
        "P3": {"pass": prob >= rules["P3"]["min_probability"], "probability": prob},
        "P4": {
            "pass": s["sharpe"] >= train_c["sharpe"] * rules["P4"]["min_ratio"],
            "train_sharpe": train_c["sharpe"],
        },
        "P5": {"pass": stressed_sharpe > comp_s["sharpe"], "stressed_sharpe": stressed_sharpe},
        "P6": {"pass": s["mdd"] * 100 >= rules["P6"]["min_mdd_pct"], "mdd": s["mdd"]},
        "P7": {
            "pass": train_c["deflated_sharpe"] >= rules["P7"]["min_deflated_sharpe"],
            "deflated_sharpe": train_c["deflated_sharpe"],
        },
    }
    checks["passed"] = all(c["pass"] for c in checks.values())
    return {
        "final": name,
        "strategy": {**s, "trades": final.trades, "taxes": final.taxes},
        "stressed": describe(stressed_result.equity),
        "benchmarks": {k: describe(v) for k, v in benches.items()},
        "comparator": comp,
        "checks": checks,
        "decision": "adopt" if checks["passed"] else "keep_index_dca",
        "equity": {name: final.equity, **benches},
    }
