"""shared/fixtures/ 재생성. backend/app/domain 또는 indicators.py를 바꾸면 같은 커밋에서 실행한다.

.venv/bin/python scripts/gen_fixtures.py
"""

from __future__ import annotations

import shutil

from research.fixtures import write_all
from research.paths import FIXTURES_DIR

CATEGORIES = ("indicators", "evaluator", "gate", "sizer", "profiles", "rebalance")


def main() -> None:
    for category in CATEGORIES:
        shutil.rmtree(FIXTURES_DIR / category, ignore_errors=True)
    written = write_all(FIXTURES_DIR)
    print(f"{len(written)}개 fixture 생성 → {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
