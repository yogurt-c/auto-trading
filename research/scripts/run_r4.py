"""R4 보수형(주식 50 · 채권 50) 검증.

    .venv/bin/python scripts/run_r4.py pre    # K1 장기 폭락 시험(2000–2019) · K2 학습 구간
    .venv/bin/python scripts/run_r4.py test   # K1·K2 통과 시에만, 검증 구간 단 1회 (잠금 파일)

결과: research/reports/r4_{pre,test}_report.json · r4_{pre,test}_equity.csv
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd
from run_backtest import _provenance, _write

from research.paths import REPORTS_DIR
from research.r2 import R2Lab, load_r2_inputs
from research.r4 import run_r4_pre_test, run_r4_test

PRE_REPORT = REPORTS_DIR / "r4_pre_report.json"
TEST_REPORT = REPORTS_DIR / "r4_test_report.json"
TEST_LOCK = REPORTS_DIR / "R4_TEST_RUN.lock"


def _clean_provenance() -> dict:
    provenance = _provenance()
    if provenance["criteria_dirty"]:
        sys.exit("config/에 커밋되지 않은 변경이 있습니다 — 사전 등록 기준이 아님")
    return provenance


def _print(stats: dict, label: str) -> None:
    for name, s in stats.items():
        print(
            f"[{label}] {name:10s} CAGR {s['cagr']:+.1%}  Sharpe {s['sharpe']:.2f}  "
            f"MDD {s['mdd']:.1%}  최장 회복 {s['longest_recovery_days']}일"
        )


def pre() -> None:
    provenance = _clean_provenance()
    report = run_r4_pre_test(R2Lab(load_r2_inputs()))
    pd.DataFrame(report.pop("equity")).to_csv(REPORTS_DIR / "r4_pre_equity.csv")
    _write(PRE_REPORT, {"provenance": provenance, **report})
    _print(report["stress"], "장기")
    _print(report["train"], "학습")
    mark = {True: "통과", False: "실패"}
    print(f"K1 {mark[report['K1']['pass']]} · K2 {mark[report['K2']['pass']]}")


def test(force: bool) -> None:
    if not PRE_REPORT.exists():
        sys.exit("r4_pre_report.json이 없습니다 — 먼저 pre를 실행하세요")
    if not json.loads(PRE_REPORT.read_text())["run_test"]:
        sys.exit("K1·K2 미통과 — 검증 구간을 쓰지 않고 안정형만 제공")
    if TEST_LOCK.exists() and not force:
        sys.exit(f"검증 구간은 이미 실행됨 ({TEST_LOCK.read_text().strip()}). 재실행은 --force")
    provenance = _clean_provenance()
    TEST_LOCK.write_text(f"{provenance['run_at']} head={provenance['head_commit']} force={force}\n")
    report = run_r4_test(R2Lab(load_r2_inputs()))
    pd.DataFrame(report.pop("equity")).to_csv(REPORTS_DIR / "r4_test_equity.csv")
    _write(TEST_REPORT, {"provenance": {**provenance, "forced": force}, **report})
    _print(report["test"], "검증")
    print(f"K3 {'통과' if report['K3']['pass'] else '실패'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["pre", "test"])
    parser.add_argument("--force", action="store_true", help="검증 구간 재실행 (기록됨)")
    args = parser.parse_args()
    if args.stage == "pre":
        pre()
    else:
        test(args.force)


if __name__ == "__main__":
    main()
