"""Integration tests for Scheduler API endpoints (pagination)."""


def test_get_scheduler_runs_paginated_structure(auth_client, db_scheduler_run):
    """GET /api/scheduler/runs → runs, total, limit, offset 포함."""
    resp = auth_client.get("/api/scheduler/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert "runs" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["runs"], list)
    assert data["total"] >= len(data["runs"])


def test_get_scheduler_runs_contains_fixture(auth_client, db_scheduler_run):
    """GET /api/scheduler/runs → fixture 데이터가 포함된다."""
    resp = auth_client.get("/api/scheduler/runs?limit=50&offset=0")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    ids = [r["id"] for r in runs]
    assert db_scheduler_run["id"] in ids

    our_run = next(r for r in runs if r["id"] == db_scheduler_run["id"])
    assert our_run["status"] == "completed"
    assert our_run["strategies_checked"] == 2
    assert our_run["orders_placed"] == 1


def test_get_scheduler_runs_limit(auth_client, db_scheduler_run):
    """GET /api/scheduler/runs?limit=1 → 1건 반환, limit 필드 반영."""
    resp = auth_client.get("/api/scheduler/runs?limit=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) <= 1
    assert data["limit"] == 1


def test_get_scheduler_runs_offset(auth_client, db_scheduler_run):
    """GET /api/scheduler/runs?offset=N → offset 필드가 응답에 반영된다."""
    resp = auth_client.get("/api/scheduler/runs?limit=10&offset=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["offset"] == 1
    assert data["limit"] == 10
    assert "total" in data


def test_get_scheduler_runs_offset_skips_items(auth_client):
    """offset=0 과 offset=1 결과가 다르다 — 테스트 내에서 2건 직접 생성."""
    from sqlalchemy import delete as sa_delete

    from app.infrastructure import repository as db
    from app.infrastructure.database import get_session
    from app.infrastructure.models import SchedulerRun as SchedulerRunModel

    run_a = db.add_scheduler_run(status="completed", summary="offset-test-A")
    run_b = db.add_scheduler_run(status="completed", summary="offset-test-B")
    try:
        resp0 = auth_client.get("/api/scheduler/runs?limit=1&offset=0")
        resp1 = auth_client.get("/api/scheduler/runs?limit=1&offset=1")
        assert resp0.status_code == 200
        assert resp1.status_code == 200
        ids0 = [r["id"] for r in resp0.json()["runs"]]
        ids1 = [r["id"] for r in resp1.json()["runs"]]
        assert ids0 != ids1
    finally:
        with get_session() as s:
            s.execute(sa_delete(SchedulerRunModel).where(
                SchedulerRunModel.id.in_([run_a["id"], run_b["id"]])
            ))


def test_get_scheduler_runs_offset_beyond_total(auth_client, db_scheduler_run):
    """offset이 total 초과 시 빈 목록, total은 실제 총 건수."""
    total_resp = auth_client.get("/api/scheduler/runs?limit=1&offset=0")
    total = total_resp.json()["total"]

    resp = auth_client.get(f"/api/scheduler/runs?limit=10&offset={total + 1000}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["runs"] == []
    assert data["total"] == total
