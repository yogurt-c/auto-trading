"""R4 보수형(주식 50 · 채권 50) — config/r4_conservative.yaml 사전 등록 그대로 실행.

안정형(R3)과 같은 실행으로 비중만 다르다. 장기 폭락 시험은 R3 합성 주식에 금리 합성 채권을 더한다.
"""

from __future__ import annotations

import pandas as pd

from research import config
from research.data.assets import fetch_fred
from research.experiment import Period
from research.r2 import R2Lab
from research.r3 import profile_stats, run_profiles, stress_assets


def bond_proxy(
    rate_pct: pd.Series, calendar: pd.DatetimeIndex, duration: float, annual_drag: float
) -> pd.DataFrame:
    """월별 금리 → 채권 가격 (시작값 10,000).

    월 수익률 = 전월 금리/12 - duration * 금리 변화 - 보수/12 를 그 달 거래일에 고르게 나눈다.
    """
    y = rate_pct.resample("MS").last().ffill() / 100
    monthly = y.shift(1) / 12 - duration * (y - y.shift(1)) - annual_drag / 12
    months = calendar.to_period("M")
    per_month = monthly.reindex(months.to_timestamp()).fillna(0.0).to_numpy()
    days_in_month = pd.Series(1, index=calendar).groupby(months).transform("size").to_numpy()
    daily = (1 + per_month) ** (1 / days_in_month) - 1
    price = pd.Series((1 + daily).cumprod() * 10_000, index=calendar)
    return pd.DataFrame(dict.fromkeys(("open", "high", "low", "close"), price))


def _profiles() -> dict[str, dict[str, float]]:
    return {
        "stable": config.load("r3_profiles")["profiles"]["stable"],
        "conservative": config.load("r4_conservative")["profile"],
    }


def run_r4_pre_test(lab: R2Lab) -> dict:
    """K1(장기 폭락 시험)·K2(학습 구간). 검증 구간은 쓰지 않는다."""
    cfg = config.load("r4_conservative")
    rules = {c["id"]: c for c in cfg["criteria"]}
    stress = config.load("r3_profiles")["stress"]
    calendar, assets = stress_assets(lab.cfg, stress)
    sb = cfg["stress_bond"]
    rate = fetch_fred(sb["rate"], "1996-12-01", stress["end"])
    assets["bond"] = bond_proxy(rate, calendar, sb["duration"], sb["annual_drag"])
    stress_days = calendar[
        (calendar >= pd.Timestamp(stress["start"])) & (calendar <= pd.Timestamp(stress["end"]))
    ]
    stress_curves = run_profiles(lab, assets, stress_days, _profiles())
    train_curves = run_profiles(lab, lab.inputs.prices, lab.days(Period.load("train")), _profiles())
    s_stats = {k: profile_stats(v) for k, v in stress_curves.items()}
    t_stats = {k: profile_stats(v) for k, v in train_curves.items()}
    cons_s, cons_t = s_stats["conservative"], t_stats["conservative"]
    k1 = cons_s["mdd"] * 100 >= rules["K1"]["min_mdd_pct"]
    k2 = cons_t["mdd"] > t_stats["stable"]["mdd"] and cons_t["cagr"] > 0
    return {
        "stress": s_stats,
        "train": t_stats,
        "K1": {"pass": k1, "conservative_mdd": cons_s["mdd"]},
        "K2": {
            "pass": k2,
            "conservative_mdd": cons_t["mdd"],
            "stable_mdd": t_stats["stable"]["mdd"],
        },
        "run_test": k1 and k2,
        "equity": {
            **{f"stress_{k}": v for k, v in stress_curves.items()},
            **{f"train_{k}": v for k, v in train_curves.items()},
        },
    }


def run_r4_test(lab: R2Lab) -> dict:
    rules = {c["id"]: c for c in config.load("r4_conservative")["criteria"]}
    curves = run_profiles(lab, lab.inputs.prices, lab.days(Period.load("test")), _profiles())
    stats = {k: profile_stats(v) for k, v in curves.items()}
    cons, stable = stats["conservative"], stats["stable"]
    k3 = cons["mdd"] * 100 >= rules["K3"]["min_mdd_pct"] and cons["mdd"] > stable["mdd"]
    return {
        "test": stats,
        "K3": {"pass": k3, "conservative_mdd": cons["mdd"], "stable_mdd": stable["mdd"]},
        "equity": {f"test_{k}": v for k, v in curves.items()},
    }
