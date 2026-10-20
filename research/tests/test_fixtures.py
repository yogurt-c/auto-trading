"""shared/fixtures/가 현재 생성기 정의와 일치하는지 확인 (생성기를 고치고 재생성을 잊은 경우).

실수는 플랫폼(macOS·Linux numpy)마다 마지막 자리가 다를 수 있어 상대오차 1e-9로 비교한다.
"""

import json
import math

from research.fixtures import build_all, render
from research.paths import FIXTURES_DIR

REL_TOL = 1e-9


def _close(a, b) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_close(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_close(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, float) or isinstance(b, float):
        return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=1e-12)
    return a == b


def test_fixtures_on_disk_match_generator():
    expected = {
        f"{category}/{name}.json": json.loads(render(content))
        for category, files in build_all().items()
        for name, content in files.items()
    }
    on_disk = {
        str(p.relative_to(FIXTURES_DIR)): json.loads(p.read_text(encoding="utf-8"))
        for p in FIXTURES_DIR.glob("*/*.json")
    }
    assert sorted(on_disk) == sorted(expected), "fixture 목록 불일치 — gen_fixtures.py 재실행"
    stale = [path for path, data in expected.items() if not _close(on_disk[path], data)]
    assert not stale, f"재생성 필요: {stale}"
