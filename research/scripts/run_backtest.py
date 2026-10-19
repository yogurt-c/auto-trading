"""P0 백테스트 실행.

    .venv/bin/python scripts/run_backtest.py train   # 학습: 필터 채택·튜닝·최종 후보·게이트
    .venv/bin/python scripts/run_backtest.py test    # 검증 구간: 최종 후보로 단 1회 (잠금 파일)

결과: research/reports/{train,test}_report.json · .md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime

import pandas as pd

from research import config
from research.data.index import load_kodex200
from research.experiment import Lab
from research.inputs import load_inputs
from research.paths import REPO_DIR, REPORTS_DIR
from research.pipeline import run_test, run_train

TRAIN_REPORT = REPORTS_DIR / "train_report.json"
TEST_REPORT = REPORTS_DIR / "test_report.json"
TEST_LOCK = REPORTS_DIR / "TEST_RUN.lock"
CRITERIA_FILES = "research/config"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_DIR, capture_output=True, text=True, check=True
    ).stdout.strip()


def _provenance() -> dict:
    dirty = _git("status", "--porcelain", "--", CRITERIA_FILES)
    return {
        "criteria_commit": _git("log", "-1", "--format=%H", "--", CRITERIA_FILES),
        "head_commit": _git("rev-parse", "HEAD"),
        "criteria_dirty": bool(dirty),
        "run_at": datetime.now().isoformat(timespec="seconds"),
    }


def _labs() -> tuple[Lab, Lab]:
    periods = config.load("periods")
    etf = load_kodex200(periods["data_start"], periods["test"]["end"])
    inputs = load_inputs()
    stressed = config.load("costs")["slippage_rate"] * 2
    return Lab(inputs, etf), Lab(inputs, etf, slippage=stressed)


def _write(path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))


def train() -> None:
    lab, _ = _labs()
    report = {"provenance": _provenance(), **run_train(lab)}
    _write(TRAIN_REPORT, report)
    gate = report["train_gate"]
    print(f"최종 후보: {report['final']['spec']['name']} ({report['final']['family']})")
    print(
        f"학습 게이트 T1: {'통과' if gate['pass'] else '실패'} "
        f"(Sharpe {gate['final_sharpe']:.3f} vs {gate['comparator_sharpe']:.3f})"
    )


def test(force: bool) -> None:
    if not TRAIN_REPORT.exists():
        sys.exit("train_report.json이 없습니다 — 먼저 train을 실행하세요")
    train_report = json.loads(TRAIN_REPORT.read_text())
    if not train_report["train_gate"]["pass"]:
        sys.exit("학습 게이트 실패 — 검증 구간을 쓰지 않고 지수 정기 매수(B2)로 결론")
    if TEST_LOCK.exists() and not force:
        sys.exit(f"검증 구간은 이미 실행됨 ({TEST_LOCK.read_text().strip()}). 재실행은 --force")
    provenance = _provenance()
    if provenance["criteria_dirty"]:
        sys.exit("config/에 커밋되지 않은 변경이 있습니다 — 사전 등록 기준이 아님")

    # 실행 전에 잠근다: 도중에 중단돼도 검증 구간을 '본 것'으로 기록
    TEST_LOCK.write_text(f"{provenance['run_at']} head={provenance['head_commit']} force={force}\n")
    lab, stressed = _labs()
    result = run_test(lab, stressed, train_report)
    equity = pd.DataFrame(result.pop("equity"))
    equity.to_csv(REPORTS_DIR / "test_equity.csv")
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
