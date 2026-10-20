"""config/*.yaml 로더."""

from __future__ import annotations

from datetime import date
from functools import cache
from typing import Any

import yaml

from research.paths import CONFIG_DIR


@cache
def load(name: str) -> dict[str, Any]:
    """config/{name}.yaml을 dict로 읽는다 (프로세스당 1회)."""
    with (CONFIG_DIR / f"{name}.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def to_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)
