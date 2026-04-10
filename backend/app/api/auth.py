"""인증 API — status, setup, login, change-password, me."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.api.deps import get_current_user
from app.infrastructure.auth import (
    create_access_token,
    get_password_hash,
    is_configured,
    set_password,
    verify_password,
)

router = APIRouter(prefix="/auth")
_limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# 공개 엔드포인트
# ---------------------------------------------------------------------------


@router.get("/status")
def auth_status():
    """앱 초기 설정 여부 반환."""
    return {"configured": is_configured()}


class PasswordRequest(BaseModel):
    password: str = Field(min_length=8)


@router.post("/setup")
@_limiter.limit("5/minute")
def setup(request: Request, body: PasswordRequest):
    """최초 비밀번호 설정 (미설정 시만 동작)."""
    if is_configured():
        raise HTTPException(status_code=409, detail="이미 설정되어 있습니다")
    set_password(body.password)
    token = create_access_token()
    return {"access_token": token, "token_type": "bearer"}


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
@_limiter.limit("5/minute")
def login(request: Request, body: LoginRequest):
    """비밀번호로 로그인 후 JWT 반환."""
    hashed = get_password_hash()
    if not hashed:
        raise HTTPException(status_code=400, detail="앱이 아직 설정되지 않았습니다")
    if not verify_password(body.password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다",
        )
    token = create_access_token()
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# 인증 필요 엔드포인트
# ---------------------------------------------------------------------------


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    _: str = Depends(get_current_user),
):
    """비밀번호 변경."""
    hashed = get_password_hash()
    if not hashed or not verify_password(body.current_password, hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 올바르지 않습니다",
        )
    set_password(body.new_password)
    return {"success": True}


@router.get("/me")
def me(_: str = Depends(get_current_user)):
    """토큰 유효성 확인용 엔드포인트."""
    return {"sub": "user"}
