"""shared/fixtures/가 현재 생성기 정의와 일치하는지 확인 (생성기를 고치고 재생성을 잊은 경우)."""

from research.fixtures import build_all, render
from research.paths import FIXTURES_DIR


def test_fixtures_on_disk_match_generator():
    expected = {
        f"{category}/{name}.json": render(content)
        for category, files in build_all().items()
        for name, content in files.items()
    }
    on_disk = {
        str(p.relative_to(FIXTURES_DIR)): p.read_text(encoding="utf-8")
        for p in FIXTURES_DIR.glob("*/*.json")
    }
    assert sorted(on_disk) == sorted(expected), "fixture 목록 불일치 — gen_fixtures.py 재실행"
    stale = [path for path, text in expected.items() if on_disk[path] != text]
    assert not stale, f"재생성 필요: {stale}"
