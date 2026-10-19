"""research 폴더 기준 경로."""

from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = RESEARCH_DIR / "config"
DATA_DIR = RESEARCH_DIR / "data"
REPORTS_DIR = RESEARCH_DIR / "reports"
REPO_DIR = RESEARCH_DIR.parent
FIXTURES_DIR = REPO_DIR / "shared" / "fixtures"
