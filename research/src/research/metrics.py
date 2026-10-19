"""성과 지표 — CAGR, Sharpe, MDD, 부트스트랩, Deflated Sharpe, 금액가중수익률."""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

TRADING_DAYS = 252
_EULER_GAMMA = 0.5772156649
_BOOTSTRAP_CHUNK = 500


def daily_returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def sharpe(returns: pd.Series, periods: int = TRADING_DAYS) -> float:
    """연환산 Sharpe (무위험 수익률 0)."""
    std = returns.std(ddof=1)
    return 0.0 if not std or math.isnan(std) else float(returns.mean() / std * math.sqrt(periods))


def cagr(equity: pd.Series) -> float:
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0


def max_drawdown(equity: pd.Series) -> float:
    """최대 낙폭 (음수, 예: -0.35)."""
    return float((equity / equity.cummax() - 1).min())


def yearly_sharpe(returns: pd.Series) -> pd.Series:
    return returns.groupby(returns.index.year).apply(sharpe)


def summary(equity: pd.Series) -> dict[str, float]:
    r = daily_returns(equity)
    mdd = max_drawdown(equity)
    growth = cagr(equity)
    return {
        "cagr": growth,
        "vol": float(r.std(ddof=1) * math.sqrt(TRADING_DAYS)),
        "sharpe": sharpe(r),
        "mdd": mdd,
        "calmar": growth / abs(mdd) if mdd else float("nan"),
        "final_equity": float(equity.iloc[-1]),
    }


def stationary_bootstrap_indices(
    n: int, reps: int, mean_block: int, rng: np.random.Generator
) -> np.ndarray:
    """Politis-Romano stationary bootstrap 인덱스 (reps x n)."""
    restart = rng.random((reps, n)) < 1 / mean_block
    restart[:, 0] = True
    starts = rng.integers(0, n, size=(reps, n))
    # 각 위치의 '마지막 재시작 지점'과 그로부터의 거리로 원래 인덱스를 만든다
    pos = np.arange(n)
    last_restart = np.maximum.accumulate(np.where(restart, pos, 0), axis=1)
    offset = pos - last_restart
    base = np.take_along_axis(starts, last_restart, axis=1)
    return (base + offset) % n


def prob_sharpe_greater(
    a: pd.Series,
    b: pd.Series,
    *,
    reps: int = 10_000,
    mean_block: int = 20,
    seed: int = 42,
) -> float:
    """같은 날짜를 함께 재표본한(paired) 부트스트랩으로 P(Sharpe_a > Sharpe_b)."""
    joined = pd.concat([a, b], axis=1, join="inner").dropna().to_numpy()
    n = len(joined)
    rng = np.random.default_rng(seed)
    wins = 0
    for done in range(0, reps, _BOOTSTRAP_CHUNK):
        k = min(_BOOTSTRAP_CHUNK, reps - done)
        idx = stationary_bootstrap_indices(n, k, mean_block, rng)
        sample = joined[idx]  # k x n x 2
        mean = sample.mean(axis=1)
        std = sample.std(axis=1, ddof=1)
        sr = np.divide(mean, std, out=np.zeros_like(mean), where=std > 0)
        wins += int((sr[:, 0] > sr[:, 1]).sum())
    return wins / reps


def deflated_sharpe(returns: pd.Series, trial_sharpes: list[float]) -> float:
    """Bailey & López de Prado Deflated Sharpe Ratio — 여러 번 시도한 것을 감안한 유의 확률.

    trial_sharpes: 시도한 모든 조합의 (연환산) Sharpe. 비교는 일간 단위로 환산해 계산한다.
    """
    n_trials = len(trial_sharpes)
    if n_trials < 2:
        raise ValueError("trial_sharpes에는 2개 이상의 시도가 필요합니다")
    norm = NormalDist()
    scale = math.sqrt(TRADING_DAYS)
    sr = sharpe(returns) / scale
    trials_var = float(np.var(np.array(trial_sharpes) / scale, ddof=1))
    sr0 = math.sqrt(trials_var) * (
        (1 - _EULER_GAMMA) * norm.inv_cdf(1 - 1 / n_trials)
        + _EULER_GAMMA * norm.inv_cdf(1 - 1 / (n_trials * math.e))
    )
    t = len(returns)
    skew = float(returns.skew())
    kurt = float(returns.kurt()) + 3  # pandas는 초과첨도
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr**2, 1e-12))
    return norm.cdf((sr - sr0) * math.sqrt(t - 1) / denom)


def money_weighted_return(flows: pd.Series, final_value: float, final_date: pd.Timestamp) -> float:
    """XIRR — flows: 날짜별 투입액(양수). 연환산 금액가중수익률."""

    def value_at_end(rate: float) -> float:
        grown = sum(
            amt * (1 + rate) ** ((final_date - d).days / 365.25) for d, amt in flows.items()
        )
        return grown - final_value

    lo, hi = -0.99, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if value_at_end(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2
