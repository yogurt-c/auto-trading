"""R2 후보 4개 백테스트 실행.

    .venv/bin/python scripts/run_r2.py train   # 학습: 후보 4개 + 기준 B1·B4, 게이트 T1·T2
    .venv/bin/python scripts/run_r2.py test    # 검증 구간: 최종 후보로 단 1회 (잠금 파일)

결과: research/reports/r2_{train,test}_report.json · r2_{train,test}_equity.csv
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd
from run_backtest import _provenance, _write

from research.paths import REPORTS_DIR
from research.r2 import R2Lab, load_r2_inputs, run_r2_test, run_r2_train

TRAIN_REPORT = REPORTS_DIR / "r2_train_report.json"
TEST_REPORT = REPORTS_DIR / "r2_test_report.json"
TEST_LOCK = REPORTS_DIR / "R2_TEST_RUN.lock"


def _require_clean(provenance: dict) -> None:
    if provenance["criteria_dirty"]:
        sys.exit("config/에 커밋되지 않은 변경이 있습니다 — 사전 등록 기준이 아님")


def train() -> None:
    provenance = _provenance()
    _require_clean(provenance)
    report = run_r2_train(R2Lab(load_r2_inputs()))
    pd.DataFrame(report.pop("equity")).to_csv(REPORTS_DIR / "r2_train_equity.csv")
    _write(TRAIN_REPORT, {"provenance": provenance, **report})
    for name, c in report["candidates"].items():
        print(
            f"{name:24s} CAGR {c['cagr']:+.1%}  Sharpe {c['sharpe']:.2f}  MDD {c['mdd']:.1%}  "
            f"게이트 {'통과' if c['gate'] else '실패'}"
        )
    print(f"최종 후보: {report['final']}")


def test(force: bool) -> None:
    if not TRAIN_REPORT.exists():
        sys.exit("r2_train_report.json이 없습니다 — 먼저 train을 실행하세요")
    train_report = json.loads(TRAIN_REPORT.read_text())
    if train_report["final"] is None:
        sys.exit("학습 게이트 통과 후보 없음 — 검증 구간을 쓰지 않고 지수 정기 매수 유지")
    if TEST_LOCK.exists() and not force:
        sys.exit(f"검증 구간은 이미 실행됨 ({TEST_LOCK.read_text().strip()}). 재실행은 --force")
    provenance = _provenance()
    _require_clean(provenance)

    # 실행 전에 잠근다: 도중에 중단돼도 검증 구간을 '본 것'으로 기록
    TEST_LOCK.write_text(f"{provenance['run_at']} head={provenance['head_commit']} force={force}\n")
    inputs = load_r2_inputs()
    result = run_r2_test(R2Lab(inputs), R2Lab(inputs, slippage_multiplier=2.0), train_report)
    pd.DataFrame(result.pop("equity")).to_csv(REPORTS_DIR / "r2_test_equity.csv")
    _write(TEST_REPORT, {"provenance": {**provenance, "forced": force}, **result})
    for pid, check in result["checks"].items():
        if pid != "passed":
            print(f"{pid}: {'통과' if check['pass'] else '실패'}")
    print(f"결론: {result['decision']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["train", "test"])
    parser.add_argument("--force", action="store_true", help="검증 구간 재실행 (기록됨)")
    args = parser.parse_args()
    if args.stage == "train":
        train()
    else:
        test(args.force)


if __name__ == "__main__":
    main()
