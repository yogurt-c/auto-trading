# AI Portfolio Manager

Claude AI 기반 국내·미국 주식 포트폴리오 관리 툴.
실시간 시세 조회, AI 분석, 매매 전략 수립, KIS(한국투자증권) 모의투자 자동 매매를 지원합니다.

## 기능

| 페이지 | 기능 |
|--------|------|
| **Dashboard** | 총 평가액·수익률(KRW/USD 분리), 자산 배분 파이차트, 종목별 P&L |
| **Holdings** | 종목 추가·수정·삭제, KIS 체결 내역 동기화(Reconcile), 거래 내역 |
| **Analysis** | AI 채팅 — 포트폴리오 분석, 시세 조회, 전략 수립 |
| **Auto Trading** | 전략 활성화/정지, KIS 계좌 잔고·주문·체결 로그, 스케줄러 설정 |
| **Settings** | KIS 앱키·계좌번호·Anthropic API 키 등록 |

## 시작하기

### 로컬 개발

```bash
make install   # 의존성 설치 (backend venv + frontend npm)
make dev       # backend + frontend 동시 실행
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Docker

```bash
# Backend
docker build --platform linux/amd64 -t portfolio-backend ./backend

# Frontend
docker build --platform linux/amd64 -t portfolio-frontend ./frontend
```

> M1/M2(Apple Silicon)에서 로컬 실행 시 `--platform linux/arm64`로 변경

### API 키 발급

앱 실행 후 **Settings 페이지**에서 직접 입력합니다 (`.env` 파일 불필요, SQLite에 저장).

| 서비스 | 발급 경로 |
|--------|----------|
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| **KIS 앱키·시크릿** | [KIS Developers](https://apiportal.koreainvestment.com) → 앱 등록 → 앱키/시크릿 확인 |
| **KIS 계좌번호** | 한국투자증권 모바일앱 → 모의투자 계좌번호 (8자리-2자리) |

## 프로젝트 구조

```
portfolio/
├── backend/                  # FastAPI (DDD 4계층)
│   ├── app/
│   │   ├── api/              # Presentation: 라우터 (auth, portfolio, strategies, trading, agent, scheduler)
│   │   ├── application/      # Application: agent, tools, scheduler
│   │   ├── domain/           # Domain: 순수 비즈니스 로직 (portfolio, trading_strategy)
│   │   └── infrastructure/   # Infrastructure: DB, KIS API, 시세(yfinance), 기술지표
│   ├── alembic/              # DB 마이그레이션
│   ├── tests/                # pytest (unit / integration / e2e)
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                 # React 18 + Vite + TypeScript
│   ├── src/
│   │   ├── api/              # axios client, SSE, types, endpoints
│   │   ├── components/       # Layout, MetricCard, DataTable, StatusBadge
│   │   └── pages/            # Dashboard, Holdings, Analysis, AutoTrading, Settings
│   ├── Dockerfile
│   └── nginx.conf
└── Makefile
```

## 에이전트 구조

```
Orchestrator (Analysis 채팅)
├── get_portfolio   — 보유 종목 조회
├── web_search      — 실시간 시세·뉴스
└── task            — 서브에이전트 위임
    ├── strategy-advisor   전략 협의 및 DB 저장
    └── trade-executor     조건 체크 → KIS 모의투자 주문
```

## 사용 예시

```
# Analysis 페이지 (AI 채팅)
"포트폴리오 현황 분석해줘"
"삼성전자 현재 주가랑 최근 뉴스 알려줘"
"AAPL 분할매수 전략 만들어줘"   → Strategy Advisor 서브에이전트 호출
```

```
# Auto Trading 페이지
전략 활성화 → Run Now
→ 활성 전략의 조건을 체크하고 조건 충족 시 KIS 모의투자 주문 실행
```

## 스키마 변경 (개발자)

```bash
# 모델 변경 후 마이그레이션 파일 자동 생성
alembic -c backend/alembic.ini revision --autogenerate -m "변경 내용 설명"

# 마이그레이션 적용
alembic -c backend/alembic.ini upgrade head

# 히스토리 확인
alembic -c backend/alembic.ini history
```

## 주의사항

- KIS **모의투자** 환경이므로 실제 자산은 사용되지 않습니다.
- API 키는 Settings 페이지에서 입력하며, `data/portfolio.db`(SQLite)에 저장됩니다.
- `data/portfolio.db` 삭제 시 모든 데이터(보유 종목, 전략, 설정)가 초기화됩니다.
- `.env` 파일은 `DB_PATH` 환경변수 전용이며, API 키 보관에 사용하지 않습니다.
