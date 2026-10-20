# 백엔드 소스코드 구조

---

## 디렉터리 트리

```
backend/
├── __init__.py
├── app/                      # DDD 구현 패키지 (소스 코드)
│   ├── __init__.py
│   ├── main.py               # FastAPI app + lifespan(init_db, ensure_started) + CORS
│   ├── api/                  # Presentation Layer — FastAPI 라우터
│   │   ├── __init__.py
│   │   ├── auth.py           # 인증 엔드포인트 (status/setup/login/change-password/me)
│   │   ├── deps.py           # FastAPI 공통 의존성 (get_current_user)
│   │   ├── portfolio.py      # GET /api/portfolio (P&L), sync, holdings, transactions, performance
│   │   ├── strategies.py     # CRUD + evaluate + dca-due
│   │   ├── trading.py        # KIS broker account, orders, logs
│   │   ├── agent.py          # SSE chat stream, trade-executor trigger
│   │   └── scheduler.py      # scheduler status/runs/trigger + settings CRUD
│   ├── application/          # Application Layer — 유스케이스 오케스트레이션
│   │   ├── __init__.py
│   │   ├── agent.py          # Orchestrator + sub-agent 루프 (Claude SDK)
│   │   ├── scheduler.py      # APScheduler 싱글톤 (ensure_started, get_status)
│   │   └── tools.py          # Agent tool 함수 + TOOL_MAP + Anthropic 스키마
│   ├── infrastructure/       # Infrastructure Layer — 기술적 구현 (DB, 외부 API)
│   │   ├── __init__.py
│   │   ├── kis_client.py     # KIS (Korea Investment & Securities) Paper Trading API 래퍼
│   │   ├── auth.py           # JWT 생성·검증, bcrypt 해싱, Secret Key 관리 (DB 기반)
│   │   ├── config.py         # Settings dataclass (SQLAlchemy 기반, 캐시)
│   │   ├── database.py       # SQLite init (Alembic), get_session() 컨텍스트매니저
│   │   ├── indicators.py     # 기술지표 calc_* + build_market_data(OHLCV → MarketData) — I/O 없음
│   │   ├── market.py         # get_current_prices() + fetch_market_data() — Yahoo Finance (yfinance)
│   │   ├── models.py         # SQLAlchemy ORM 모델 (Holding, Strategy, TradeLog …)
│   │   └── repository.py     # Data Access Layer — 전체 테이블 CRUD 함수
│   └── domain/               # Domain Layer — 순수 비즈니스 로직 (I/O 없음)
│       ├── __init__.py
│       ├── portfolio/
│       │   ├── __init__.py
│       │   ├── services.py   # PortfolioValuationService, RealizedPnlAggregator
│       │   └── value_objects.py  # Money, HoldingValuation, PortfolioSnapshot, RealizedTradeVO, PerformanceSummary
│       └── trading_strategy/
│           ├── __init__.py
│           ├── services.py   # StrategyEvaluator, DcaScheduleChecker, StrategyValidator
│           └── value_objects.py  # MarketData, EvaluationResult, ValidationWarning
├── requirements.txt          # 백엔드 전용 의존성
├── pytest.ini                # pytest 설정 (pythonpath=.., testpaths=tests)
├── .env.example              # 백엔드 환경변수 예시
├── alembic.ini               # Alembic 설정 (script_location = %(here)s/alembic)
├── alembic/                  # DB 스키마 마이그레이션
│   ├── env.py
│   └── versions/
│           ├── 001_initial_schema.py             # KIS 브로커 통합 전체 스키마 (market/currency 포함)
│           └── 002_add_indicator_entry_conditions.py  # 기술지표 진입 조건 컬럼 5개 추가
└── tests/                    # pytest (unit + integration + e2e)
    ├── conftest.py
    ├── unit/domain/
    ├── integration/
    └── e2e/
```

---

## 파일별 역할

### `backend/app/api/` — Presentation Layer

| 파일 | 역할 | 주요 의존성 |
|------|------|------------|
| `auth.py` | 인증 REST 엔드포인트 (공개+보호) | `app.infrastructure.auth`, `app.api.deps`, slowapi rate limiter |
| `deps.py` | `get_current_user` FastAPI dependency | `app.infrastructure.auth` |
| `portfolio.py` | 포트폴리오 REST 엔드포인트 | `app.infrastructure.repository`, `app.infrastructure.market`, `app.domain.portfolio.services` |
| `strategies.py` | 전략 CRUD + 평가 엔드포인트 | `app.infrastructure.repository`, `app.application.tools` |
| `trading.py` | KIS 계좌·주문·로그 엔드포인트 | `app.infrastructure.kis_client`, `app.infrastructure.repository`, `app.application.tools` |
| `agent.py` | SSE 스트리밍·trade-executor 엔드포인트 | `app.application.agent` |
| `scheduler.py` | 스케줄러 상태·settings CRUD 엔드포인트 | `app.application.scheduler`, `app.infrastructure.repository`, `app.infrastructure.config`, `app.infrastructure.kis_client` |

### `backend/app/application/` — Application Layer

| 파일 | 역할 | 비고 |
|------|------|------|
| `agent.py` | Orchestrator + sub-agent agentic loop | Anthropic SDK, prompt caching, SSE generator |
| `scheduler.py` | APScheduler 싱글톤 | `ensure_started()` — FastAPI lifespan에서 호출 |
| `tools.py` | Agent tool 구현체 + Anthropic 스키마 | domain service를 모듈 레벨 싱글톤으로 사용 |

### `backend/app/infrastructure/` — Infrastructure Layer

| 파일 | 역할 | 비고 |
|------|------|------|
| `kis_client.py` | KIS TradingClient 싱글톤 래퍼 | `reset_client()` — 설정 변경 시 호출; `is_korean_ticker()`, `ticker_market()`, `ticker_currency()` 유틸 |
| `auth.py` | JWT 생성·검증, bcrypt 비밀번호 해싱 | `__SECRET_KEY__`·`APP_PASSWORD_HASH`를 Settings 테이블에 저장 |
| `config.py` | Settings 캐시 (SQLAlchemy 기반) | `reload_settings()` — 설정 저장 후 호출 |
| `database.py` | SQLite 초기화 (Alembic auto-migrate) | `get_session()` — context manager |
| `market.py` | `get_current_prices(tickers)` | yfinance, 6자리 한국 티커는 자동으로 `.KS` suffix 추가, 실패 티커는 결과에서 제외 |
| `models.py` | ORM: Holding, Strategy, TradeLog, RealizedTrade, Setting, SchedulerRun | market/currency 필드 추가됨. **dict key 접근 시 반드시 이 파일의 컬럼명을 참조할 것** — Holding: `shares`(NOT quantity), TradeLog: `qty`·`side`(NOT shares·action) |
| `repository.py` | 전체 DB CRUD 함수 | get_all_holdings, save_strategy, add_trade_log, add_realized_trade, get_realized_trades … |

### `backend/app/domain/` — Domain Layer

| 파일 | 역할 | 비고 |
|------|------|------|
| `portfolio/services.py` | `PortfolioValuationService.calculate()`, `RealizedPnlAggregator.aggregate()` | I/O 없음, 순수 계산 |
| `portfolio/value_objects.py` | `Money`, `HoldingValuation`, `PortfolioSnapshot`, `RealizedTradeVO`, `PeriodPnl`, `StrategyPnl`, `PerformanceSummary` | Pydantic v2, frozen=True |
| `trading_strategy/services.py` | `StrategyEvaluator`, `DcaScheduleChecker`, `StrategyValidator` | I/O 없음, 순수 계산 |
| `trading_strategy/value_objects.py` | `MarketData`, `EvaluationResult`, `ValidationWarning` | Pydantic v2, frozen=True |

---

## 레이어 간 의존 방향

```
Presentation (api/)
    └─▶ Application (application/)
    └─▶ Infrastructure (infrastructure/)
    └─▶ Domain (domain/)

Application (application/)
    └─▶ Infrastructure (infrastructure/)
    └─▶ Domain (domain/)

Infrastructure (infrastructure/)
    └─▶ Domain (domain/)

Domain (domain/)   ← 외부 의존성 없음 (순수 Python + Pydantic)
```

**규칙:**
- `backend/app/api/`는 `backend/app/application/` · `backend/app/infrastructure/` · `backend/app/domain/` 임포트 가능
- `backend/app/application/`는 `backend/app/infrastructure/` · `backend/app/domain/` 임포트 가능
- `backend/app/infrastructure/`는 `backend/app/domain/` 임포트 가능
- `backend/app/domain/`은 외부 의존성 없음

---

## 실행 방법

```bash
# 백엔드 단독 실행
make backend     # uvicorn app.main:app --reload --port 8000

# 테스트
pytest -c backend/pytest.ini

# Alembic 마이그레이션
alembic -c backend/alembic.ini upgrade head
```

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DB_PATH` | `data/portfolio.db` | SQLite DB 경로 (프로젝트 루트 기준) |

API 키 (`ANTHROPIC_API_KEY`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `KIS_ACCOUNT_NO`)는 `.env` 파일이 아닌 **SQLite settings 테이블**에 저장됨.
