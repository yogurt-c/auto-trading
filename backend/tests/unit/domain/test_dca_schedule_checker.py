"""Unit tests for DcaScheduleChecker."""

from datetime import datetime, timedelta, timezone

import pytest

from domain.trading_strategy.services import DcaScheduleChecker


@pytest.fixture
def checker():
    return DcaScheduleChecker()


def test_no_frequency(checker):
    """dca_frequency_days 없음 → is_due=False."""
    result = checker.is_due({"dca_frequency_days": None})
    assert result["is_due"] is False


def test_no_frequency_missing_key(checker):
    """dca_frequency_days 키 자체 없음 → is_due=False."""
    result = checker.is_due({})
    assert result["is_due"] is False


def test_never_triggered(checker):
    """last_triggered_at=None → is_due=True (한 번도 실행 안 됨)."""
    result = checker.is_due({"dca_frequency_days": 7, "last_triggered_at": None})
    assert result["is_due"] is True
    assert "Never" in result["reason"]


def test_due(checker):
    """days_since(10) >= freq(7) → is_due=True."""
    now = datetime.now(timezone.utc)
    last = now - timedelta(days=10)
    result = checker.is_due(
        {"dca_frequency_days": 7, "last_triggered_at": last},
        now=now,
    )
    assert result["is_due"] is True
    assert result["days_since_last"] == pytest.approx(10.0, abs=0.01)


def test_not_due(checker):
    """days_since(3) < freq(7) → is_due=False."""
    now = datetime.now(timezone.utc)
    last = now - timedelta(days=3)
    result = checker.is_due(
        {"dca_frequency_days": 7, "last_triggered_at": last},
        now=now,
    )
    assert result["is_due"] is False
    assert result["days_since_last"] == pytest.approx(3.0, abs=0.01)


def test_string_last_triggered(checker):
    """last_triggered_at이 ISO 문자열일 때 파싱 후 정상 동작."""
    now = datetime.now(timezone.utc)
    last_str = (now - timedelta(days=10)).isoformat()
    result = checker.is_due(
        {"dca_frequency_days": 7, "last_triggered_at": last_str},
        now=now,
    )
    assert result["is_due"] is True


def test_naive_datetime(checker):
    """timezone-naive last_triggered_at → UTC로 처리."""
    now = datetime.now(timezone.utc)
    last_naive = (now - timedelta(days=10)).replace(tzinfo=None)
    result = checker.is_due(
        {"dca_frequency_days": 7, "last_triggered_at": last_naive},
        now=now,
    )
    assert result["is_due"] is True


def test_exactly_on_due_date(checker):
    """days_since == freq → is_due=True (경계값)."""
    now = datetime.now(timezone.utc)
    last = now - timedelta(days=7)
    result = checker.is_due(
        {"dca_frequency_days": 7, "last_triggered_at": last},
        now=now,
    )
    assert result["is_due"] is True
