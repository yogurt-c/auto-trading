# AI Portfolio Manager

Claude AI 기반 미국 주식/ETF 포트폴리오 관리 툴.
실시간 시세 조회, AI 분석, 매매 전략 수립, Alpaca Paper Trading 자동 매매를 지원합니다.

## 기능

| 페이지 | 기능 |
|--------|------|
| **Dashboard** | 총 평가액·수익률, 자산 배분 파이차트, 종목별 P&L |
| **Holdings** | 종목 추가·수정·삭제, 거래 내역 |
| **Analysis** | AI 채팅 — 포트폴리오 분석, 시세 조회, 전략 수립 |
| **Auto Trading** | 전략 활성화/정지, Alpaca 잔고 확인, 매매 로그 |

## 시작하기

### Docker

```bash
# Backend
docker build --platform linux/amd64 -t portfolio-backend ./backend

# Frontend
docker build --platform linux/amd64 -t portfolio-frontend ./frontend
```

데이터는 `~/portfolio-data/`에 영구 저장됩니다.

> M1/M2(Apple Silicon)에서 로컬 실행 시 `--platform linux/arm64`로 변경

#### API 키 발급 위치

- **Anthropic** → [console.anthropic.com](https://console.anthropic.com) → API Keys
- **Alpaca** → [alpaca.markets](https://alpaca.markets) 가입 → 대시보드 상단 **Paper Trading** 선택 → **Your API Keys** → Generate New Key

### 로컬 개발

```bash
make install   # 의존성 설치
make dev       # backend + frontend 동시 실행
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## 프로젝트 구조

```
portfolio/
├── backend/                  # FastAPI (DDD 4계층)
│   ├── api/                  # Presentation: 라우터
│   ├── application/          # Application: agent, tools, scheduler
│   ├── domain/               # Domain: 순수 비즈니스 로직
│   ├── infrastructure/       # Infrastructure: DB, Alpaca, 시세
│   ├── alembic/              # DB 마이그레이션
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                 # React + Vite + TypeScript
│   ├── src/
│   │   ├── api/              # axios client, SSE, types
│   │   ├── components/       # 공통 컴포넌트
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
    └── trade-executor     조건 체크 → Alpaca 주문
```

## 사용 예시

```
# Analysis 페이지 (AI 채팅)
"포트폴리오 현황 분석해줘"
"AAPL 현재 주가랑 최근 뉴스 알려줘"
"AAPL 분할매수 전략 만들어줘"   → Strategy Advisor 서브에이전트 호출
```

```
# Auto Trading 페이지
전략 활성화 → Run Now
→ 활성 전략의 조건을 체크하고 조건 충족 시 Alpaca Paper Trading 주문 실행
```

## 스키마 변경 (개발자)

```bash
# 모델 변경 후 마이그레이션 파일 자동 생성
alembic revision --autogenerate -m "변경 내용 설명"

# 마이그레이션 적용
alembic upgrade head

# 히스토리 확인
alembic history
```

## 주의사항

- `ALPACA_PAPER=true` 상태에서는 실제 돈이 사용되지 않습니다.
- `data/portfolio.db`는 로컬 SQLite 파일로, 삭제 시 모든 데이터가 초기화됩니다.
- `.env` 파일은 `.gitignore`에 포함되어 있어 커밋되지 않습니다.
