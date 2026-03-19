"""Integration tests for Auth API endpoints."""

import bcrypt as _bcrypt
from sqlalchemy import delete as sa_delete

from app.infrastructure import repository as db
from app.infrastructure.database import get_session
from app.infrastructure.models import Setting as SettingModel

_HASH_KEY = "APP_PASSWORD_HASH"


def _hash(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _clear_password_hash():
    with get_session() as s:
        s.execute(sa_delete(SettingModel).where(SettingModel.key == _HASH_KEY))


# ---------------------------------------------------------------------------
# 공개 엔드포인트 테스트
# ---------------------------------------------------------------------------


def test_status_not_configured(app_client):
    """DB 미설정 시 configured=false."""
    _clear_password_hash()
    resp = app_client.get("/api/auth/status")
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


def test_setup_success(app_client):
    """POST /auth/setup → access_token 반환."""
    _clear_password_hash()
    resp = app_client.post("/api/auth/setup", json={"password": "test-pass-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # cleanup
    _clear_password_hash()


def test_setup_already_configured(app_client):
    """이미 설정된 경우 409."""
    _clear_password_hash()
    app_client.post("/api/auth/setup", json={"password": "test-pass-123"})
    resp = app_client.post("/api/auth/setup", json={"password": "another-pass"})
    assert resp.status_code == 409
    # cleanup
    _clear_password_hash()


def test_login_success(app_client):
    """올바른 비밀번호 → access_token."""
    _clear_password_hash()
    db.save_setting(_HASH_KEY, _hash("mypassword123"))
    try:
        resp = app_client.post("/api/auth/login", json={"password": "mypassword123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
    finally:
        _clear_password_hash()


def test_login_wrong_password(app_client):
    """잘못된 비밀번호 → 401."""
    _clear_password_hash()
    db.save_setting(_HASH_KEY, _hash("correctpassword"))
    try:
        resp = app_client.post("/api/auth/login", json={"password": "wrongpassword"})
        assert resp.status_code == 401
    finally:
        _clear_password_hash()


def test_protected_without_token(app_client):
    """Bearer 없이 GET /api/portfolio → 401."""
    resp = app_client.get("/api/portfolio")
    assert resp.status_code == 401


def test_protected_with_valid_token(app_client):
    """유효 토큰 → 200 (portfolio는 holdings mock 없이도 빈 응답 반환)."""
    from unittest.mock import patch

    _clear_password_hash()
    db.save_setting(_HASH_KEY, _hash("validpass"))
    try:
        login_resp = app_client.post("/api/auth/login", json={"password": "validpass"})
        token = login_resp.json()["access_token"]
        with patch("app.api.portfolio.db.get_all_holdings", return_value=[]):
            resp = app_client.get(
                "/api/portfolio",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
    finally:
        _clear_password_hash()


# ---------------------------------------------------------------------------
# 인증 필요 엔드포인트 테스트 (auth_client fixture 사용)
# ---------------------------------------------------------------------------


def test_change_password_success(auth_client):
    """현재 비밀번호 + 새 비밀번호 → success=True."""
    # 다른 app_client 테스트가 hash를 지울 수 있으므로 직접 설정
    db.save_setting(_HASH_KEY, _hash("test-password-123"))

    resp = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "test-password-123", "new_password": "new-pass-456"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # 원래 비밀번호로 복구
    db.save_setting(_HASH_KEY, _hash("test-password-123"))


def test_change_password_wrong_current(auth_client):
    """현재 비밀번호 틀림 → 401."""
    # 다른 테스트가 hash를 지울 수 있으므로 직접 설정
    db.save_setting(_HASH_KEY, _hash("test-password-123"))

    resp = auth_client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong-current", "new_password": "new-pass-789"},
    )
    assert resp.status_code == 401


def test_me_with_valid_token(auth_client):
    """GET /auth/me → { sub: 'user' }."""
    resp = auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json()["sub"] == "user"


def test_me_without_token(app_client):
    """토큰 없이 GET /auth/me → 401."""
    resp = app_client.get("/api/auth/me")
    assert resp.status_code == 401
