"""FastAPI 백엔드 진입점."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# backend/ 기준 절대경로로 .env 로드 — override=False이므로 이미 set된 환경변수는 유지됨
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import agent, portfolio, scheduler, strategies, trading
from app.api.auth import router as auth_router
from app.application.scheduler import ensure_started
from app.infrastructure.auth import get_or_create_secret_key
from app.infrastructure.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    get_or_create_secret_key()  # 서버 시작 시 Secret Key 초기화
    ensure_started()
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Portfolio API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:4173",  # Vite preview
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(auth_router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(trading.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(scheduler.router, prefix="/api")
