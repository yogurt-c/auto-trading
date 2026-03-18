"""FastAPI 백엔드 진입점."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.infrastructure.database import init_db
from app.application.scheduler import ensure_started
from app.api import portfolio, strategies, trading, agent, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ensure_started()
    yield


app = FastAPI(title="Portfolio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",   # Streamlit (호환)
        "http://localhost:46131",  # 기존 개발환경
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(portfolio.router, prefix="/api")
app.include_router(strategies.router, prefix="/api")
app.include_router(trading.router, prefix="/api")
app.include_router(agent.router, prefix="/api")
app.include_router(scheduler.router, prefix="/api")
