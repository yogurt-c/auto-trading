# 프론트엔드 소스코드 구조

---

## 디렉터리 트리

```
frontend/
├── index.html
├── package.json              # React 18, Vite, Emotion, Radix UI, Recharts, TanStack Query
├── vite.config.ts            # dev proxy: /api → http://localhost:8000
├── tsconfig*.json
├── .env.example              # VITE_API_BASE_URL (기본: Vite proxy /api)
└── src/
    ├── vite-env.d.ts         # import.meta.env 타입 참조
    ├── main.tsx              # 진입점: QueryClientProvider + Global CSS
    ├── App.tsx               # React Router 라우트 정의
    ├── theme.ts              # 다크테마 디자인 토큰 (colors, spacing, fontSize 등)
    ├── api/
    │   ├── types.ts          # TS 인터페이스 (Holding, Strategy, TradeLog 등)
    │   ├── client.ts         # axios 인스턴스 (baseURL = VITE_API_BASE_URL ?? /api)
    │   ├── endpoints.ts      # portfolioApi, strategiesApi, tradingApi, schedulerApi, settingsApi
    │   └── sseClient.ts      # streamChat() AsyncGenerator — fetch + ReadableStream
    ├── components/
    │   ├── Layout.tsx        # 사이드바 네비게이션 (NavLink 5개)
    │   ├── MetricCard.tsx    # 수치 지표 카드 (title, value, delta)
    │   ├── DataTable.tsx     # 제네릭 테이블 (columns + data, constraint 없음)
    │   └── StatusBadge.tsx   # 상태 배지 (active/paused/failed/pending 색상)
    └── pages/
        ├── Dashboard.tsx     # PieChart + BarChart + 수동 가격 입력 + 60s 자동갱신
        ├── Holdings.tsx      # Alpaca 동기화 버튼 + 보유종목/거래내역 테이블
        ├── Analysis.tsx      # SSE 채팅 UI (AsyncGenerator 스트리밍)
        ├── AutoTrading.tsx   # Radix Tabs/Switch/Select + 전략 카드 + 스케줄러
        └── Settings.tsx      # API 키 3개 입력 + 저장 토스트
```

---

## 파일별 역할

### `frontend/src/api/`

| 파일 | 역할 | 비고 |
|------|------|------|
| `types.ts` | 백엔드 응답 TS 인터페이스 전체 | Holding, Strategy, TradeLog, SchedulerRun 등 |
| `client.ts` | axios 인스턴스 | `VITE_API_BASE_URL` env var (기본: `/api` → Vite proxy) |
| `endpoints.ts` | 타입화된 API 함수 모음 | portfolioApi, strategiesApi, tradingApi, schedulerApi, settingsApi |
| `sseClient.ts` | SSE 스트리밍 | `streamChat()` AsyncGenerator, `fetch()` + `ReadableStream` |

### `frontend/src/components/`

| 파일 | 역할 | 비고 |
|------|------|------|
| `Layout.tsx` | 사이드바 네비게이션 | NavLink 5개 (Dashboard/Holdings/Analysis/AutoTrading/Settings) |
| `MetricCard.tsx` | 수치 지표 카드 | title, value, delta props |
| `DataTable.tsx` | 제네릭 테이블 | `DataTable<T>` — constraint 없음, 내부에서 `Record<string, any>` cast |
| `StatusBadge.tsx` | 상태 배지 | active/paused/failed/pending 색상 매핑 |

### `frontend/src/pages/`

| 파일 | 역할 | 주요 API 호출 |
|------|------|--------------|
| `Dashboard.tsx` | P&L 대시보드 (60s 자동갱신, 차트 2개) | `GET /api/portfolio` |
| `Holdings.tsx` | 보유 종목·거래내역 + Alpaca 동기화 | `GET /api/holdings`, `POST /api/portfolio/sync` |
| `Analysis.tsx` | AI 채팅 (SSE 스트리밍) | `POST /api/agent/chat/stream` |
| `AutoTrading.tsx` | 전략·스케줄러·로그 관리 | `/api/strategies/*`, `/api/scheduler/*`, `/api/trading/*` |
| `Settings.tsx` | API 키 등록 | `GET /api/settings`, `PUT /api/settings/{key}` |

---

## 규칙

- `frontend/src/pages/`는 `frontend/src/api/`만 사용 (`backend/` 직접 임포트 금지)
- `DataTable<T>`는 제네릭 constraint 없음 — 내부에서 `Record<string, any>` cast

---

## 실행 방법

```bash
# 개발 서버 (http://localhost:5173)
make frontend    # cd frontend && npm run dev

# 프로덕션 빌드
cd frontend && npm run build
```

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VITE_API_BASE_URL` | (빈값 → Vite proxy `/api`) | axios baseURL; 프로덕션에서만 명시 설정 |
