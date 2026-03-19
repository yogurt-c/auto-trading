"""인증 인프라 — JWT, 비밀번호 해싱, Secret Key 관리 (DB 기반)."""

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

from .repository import get_setting, save_setting

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 7
_SECRET_KEY_SETTING = "__SECRET_KEY__"
_PASSWORD_HASH_SETTING = "APP_PASSWORD_HASH"


def get_or_create_secret_key() -> str:
    """DB에서 Secret Key를 로드하거나, 없으면 생성 후 저장."""
    key = get_setting(_SECRET_KEY_SETTING)
    if not key:
        key = secrets.token_hex(32)
        save_setting(_SECRET_KEY_SETTING, key)
    return key


def is_configured() -> bool:
    """APP_PASSWORD_HASH가 DB에 설정되어 있는지 확인."""
    return bool(get_setting(_PASSWORD_HASH_SETTING))


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt로 비밀번호 검증."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def set_password(new_password: str) -> None:
    """bcrypt 해시를 생성하여 DB에 저장."""
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    save_setting(_PASSWORD_HASH_SETTING, hashed)


def get_password_hash() -> str | None:
    """저장된 비밀번호 해시 반환."""
    return get_setting(_PASSWORD_HASH_SETTING)


def create_access_token(expires_delta: timedelta | None = None) -> str:
    """JWT 액세스 토큰 생성."""
    secret_key = get_or_create_secret_key()
    expire = datetime.now(UTC) + (
        expires_delta if expires_delta else timedelta(days=_TOKEN_EXPIRE_DAYS)
    )
    payload = {"sub": "user", "exp": expire}
    return jwt.encode(payload, secret_key, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """JWT 검증 후 payload 반환. 실패 시 JWTError 발생."""
    secret_key = get_or_create_secret_key()
    return jwt.decode(token, secret_key, algorithms=[_ALGORITHM])
