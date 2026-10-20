"""R3 앱 투자 성향 2종 (안정형·공격형) — config/r3_profiles.yaml 사전 등록 그대로 실행.

두 성향 모두 고정 비중 월 리밸런싱(r2.fixed_mix_targets + rotation.run_rotation)이고 비중만 다르다.
장기 폭락 시험(2000–2019)은 국내 ETF가 없던 시기라 국내·미국 자산을 모두 지수로 합성한다.
"""

from __future__ import annotations

import pandas as pd

from research import config
from research.data.assets import (
    fetch_fred,
    fetch_yf,
    leveraged_index,
    synthetic_krw_etf,
)
from research.experiment import Period
from research.r2 import R2Lab, describe, fixed_mix_targets
from research.rotation import run_rotation

PROFILES = ("stable", "aggressive")


def longest_recovery_days(equity: pd.Series) -> int:
    """고점에서 그 고점을 회복하기까지 걸린 최장 달력일 수 (기간 끝까지 미회복이면 끝까지)."""
    peak_day = equity.index[0]
    peak = equity.iloc[0]
    longest = 0
    for day, value in equity.items():
        if value >= peak:
            longest = max(longest, (day - peak_day).days)
            peak_day, peak = day, value
    return max(longest, (equity.index[-1] - peak_day).days)


def profile_stats(equity: pd.Series) -> dict:
    yearly = equity.groupby(equity.index.year).last()
    yearly_ret = yearly / yearly.shift(1).fillna(equity.iloc[0]) - 1
    return {
        **describe(equity),
        "longest_recovery_days": longest_recovery_days(equity),
        "worst_year": int(yearly_ret.idxmin()),
        "worst_year_return": float(yearly_ret.min()),
        "yearly": {int(y): float(v) for y, v in yearly_ret.items()},
    }


def stress_assets(r2_cfg: dict, stress: dict) -> tuple[pd.DatetimeIndex, dict[str, pd.DataFrame]]:
    """장기 시험용 합성 자산. 국내는 코스피 종합 가격지수(원화), 미국은 S&P500 총수익 x 환율."""
    start, end = "1996-12-01", str((pd.Timestamp(stress["end"]) + pd.Timedelta(days=1)).date())
    kospi = fetch_yf(stress["kr_index"], start, end)["close"]
    calendar = pd.DatetimeIndex(kospi.index)
    kr_rate = fetch_fred(stress["kr_rate"], start, end)
    assets = {}
    for name, leverage, drag in (
        ("kr_1x", 1, stress["kr_1x_annual_drag"]),
        ("kr_2x", 2, stress["kr_2x_annual_drag"]),
    ):
        # 국내 지수는 장 마감 후 바로 알 수 있으므로 하루 늦춰 쓰는 미국 합성과 달리 당일 값을 쓴다
        idx = leveraged_index(kospi, kr_rate, leverage, drag)
        assets[name] = pd.DataFrame(dict.fromkeys(("open", "high", "low", "close"), idx * 10_000))
    fx = fetch_fred(r2_cfg["synthetic"]["fx"], start, end)
    us_rate = fetch_fred(r2_cfg["synthetic"]["rate"], start, end)
    tr = fetch_yf("^SP500TR", start, end)["close"]
    for name in ("us_1x", "us_2x"):
        spec = r2_cfg["assets"][name]
        usd = leveraged_index(tr, us_rate, spec["leverage"], spec["annual_drag"])
        assets[name] = synthetic_krw_etf(usd, fx, calendar)
    return calendar, assets


def run_profiles(
    lab: R2Lab,
    prices: dict[str, pd.DataFrame],
    days: pd.DatetimeIndex,
    profiles: dict[str, dict[str, float]] | None = None,
) -> dict[str, pd.Series]:
    """성향별 고정 비중 월 리밸런싱 평가액. profiles 기본값 = R3 안정형·공격형."""
    profiles = profiles or {n: config.load("r3_profiles")["profiles"][n] for n in PROFILES}
    return {
        name: run_rotation(
            name,
            prices,
            fixed_mix_targets(profiles[name], days),
            days,
            lab.capital,
            lab.asset_costs,
        ).equity
        for name in profiles
    }


def run_r3_pre_test(lab: R2Lab) -> dict:
    """G1(장기 폭락 시험)·G2(학습 구간). 검증 구간은 쓰지 않는다."""
    cfg = config.load("r3_profiles")
    rules = {c["id"]: c for c in cfg["criteria"]}
    stress = cfg["stress"]
    calendar, assets = stress_assets(lab.cfg, stress)
    stress_days = calendar[
        (calendar >= pd.Timestamp(stress["start"])) & (calendar <= pd.Timestamp(stress["end"]))
    ]
    stress_curves = run_profiles(lab, assets, stress_days)
    train = Period.load("train")
    train_curves = run_profiles(lab, lab.inputs.prices, lab.days(train))

    s_stats = {k: profile_stats(v) for k, v in stress_curves.items()}
    t_stats = {k: profile_stats(v) for k, v in train_curves.items()}
    g1 = s_stats["aggressive"]["mdd"] * 100 >= rules["G1"]["min_mdd_pct"]
    g2 = t_stats["aggressive"]["cagr"] > t_stats["stable"]["cagr"]
    return {
        "stress": s_stats,
        "train": t_stats,
        "G1": {"pass": g1, "aggressive_mdd": s_stats["aggressive"]["mdd"]},
        "G2": {
            "pass": g2,
            "aggressive_cagr": t_stats["aggressive"]["cagr"],
            "stable_cagr": t_stats["stable"]["cagr"],
        },
        "run_test": g1 and g2,
        "equity": {
            **{f"stress_{k}": v for k, v in stress_curves.items()},
            **{f"train_{k}": v for k, v in train_curves.items()},
        },
    }


def run_r3_test(lab: R2Lab) -> dict:
    rules = {c["id"]: c for c in config.load("r3_profiles")["criteria"]}
    curves = run_profiles(lab, lab.inputs.prices, lab.days(Period.load("test")))
    stats = {k: profile_stats(v) for k, v in curves.items()}
    aggr, stable = stats["aggressive"], stats["stable"]
    g3 = aggr["cagr"] > stable["cagr"] and aggr["mdd"] * 100 >= rules["G3"]["min_mdd_pct"]
    return {
        "test": stats,
        "G3": {"pass": g3, "aggressive_cagr": aggr["cagr"], "aggressive_mdd": aggr["mdd"]},
        "equity": {f"test_{k}": v for k, v in curves.items()},
    }
