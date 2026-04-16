# Architecture: DDD 4계층 + Backend/Frontend Split

---

## 전체 레이어 구조

```mermaid
graph TB
    subgraph FE["Frontend (React+Vite :5173)"]
        P0[pages/Settings.tsx]
        P1[pages/Dashboard.tsx]
        P2[pages/Holdings.tsx]
        P3[pages/Analysis.tsx]
        P4[pages/AutoTrading.tsx]
        AC[api/endpoints.ts + sseClient.ts<br/>axios / fetch 래퍼]
        P0 & P1 & P2 & P3 & P4 --> AC
    end

    HTTP{{"HTTP / SSE\n:8000"}}

    subgraph BE["Presentation Layer (backend/api/ :8000)"]
        B1[api/portfolio.py<br/>GET /api/portfolio/*]
        B2[api/strategies.py<br/>CRUD /api/strategies/*]
        B3[api/trading.py<br/>GET /api/trading/*]
        B4[api/agent.py<br/>POST /api/agent/* SSE]
        B5[api/scheduler.py<br/>GET /api/scheduler/*<br/>PUT /api/settings/*]
    end

    subgraph Application["Application Layer (backend/application/)"]
        A1[agent.py<br/>stream_orchestrator<br/>Orchestrator Agent]
        A2[agent.py<br/>run_trade_executor<br/>Trade Executor Sub-agent]
        A3[scheduler.py<br/>_job · ensure_started<br/>APScheduler]
        AT[tools.py<br/>Agent Tool Functions · I/O Dispatch]
    end

    subgraph Domain["Domain Layer (backend/domain/)"]
        subgraph BC1["Bounded Context: Portfolio"]
            D1[PortfolioValuationService]
            D2[Money · HoldingValuation<br/>PortfolioSnapshot]
        end
        subgraph BC2["Bounded Context: TradingStrategy"]
            D3[StrategyEvaluator]
            D4[DcaScheduleChecker]
            D5[StrategyValidator]
            D6[MarketData · EvaluationResult<br/>ValidationWarning]
        end
    end

    subgraph Infra["Infrastructure Layer (backend/infrastructure/)"]
        I1[repository.py<br/>SQLite DAL]
        I2[kis_client.py<br/>KIS Paper Trading]
        I3[market.py<br/>Yahoo Finance]
        I4[database.py + models.py<br/>SQLAlchemy ORM]
        I5[config.py<br/>Settings 캐시]
    end

    subgraph External["External Services"]
        E1[(data/portfolio.db<br/>SQLite)]
        E2[KIS API]
        E3[Yahoo Finance]
        E4[Claude API<br/>Sonnet 4.6 / Haiku 4.5]
    end

    AC -->|REST / SSE| HTTP
    HTTP --> B1 & B2 & B3 & B4 & B5

    B1 --> D1 & I1 & I3
    B2 --> I1 & AT
    B3 --> I2 & I1 & AT
    B4 --> A1 & A2
    B5 --> A3 & I1

    A1 & A2 -->|Tool calls| AT
    A3 --> A2
    A1 & A2 --> I5

    AT --> I1 & I2 & I3
    AT --> D3 & D4 & D5

    I1 --> I4 --> E1
    I2 --> I5
    I2 --> E2
    I3 --> E3
    A1 & A2 --> E4
```

---

## 도메인 간 관계

```mermaid
graph LR
    subgraph Portfolio
        H[Holding<br/>ticker · shares · avg_price]
    end

    subgraph TradingStrategy
        S[Strategy<br/>id · ticker · type · status]
        TL[TradeLog<br/>실행 이력]
        S -->|1:N| TL
    end

    S -->|ticker 참조| H
    TL -->|주문 완료 후<br/>KIS Position Sync| H
```

---

## Agent 실행 흐름 (채팅 + 자동매매)

```mermaid
sequenceDiagram
    actor User
    participant UI as React<br/>Analysis.tsx
    participant AC as sseClient.ts
    participant BAPI as api/agent.py
    participant Orch as Orchestrator<br/>application/agent.py
    participant Advisor as Strategy Advisor<br/>Sub-agent
    participant Exec as Trade Executor<br/>Sub-agent
    participant Tools as application/tools.py
    participant Domain as domain/ services
    participant DB as SQLite
    participant Alpaca as KIS API

    rect rgb(230, 245, 255)
        Note over User,Alpaca: 채팅 흐름 (SSE 스트리밍)
        User->>UI: 전략 생성 요청 (자연어)
        UI->>AC: streamChat(msg, history)
        AC->>BAPI: POST /api/agent/chat/stream
        BAPI->>Orch: stream_orchestrator()
        Orch->>Advisor: Task tool 위임
        Advisor->>Tools: save_strategy()
        Tools->>Domain: StrategyValidator.validate()
        Tools->>DB: Strategy INSERT
        BAPI-->>AC: SSE data chunks
        AC-->>UI: AsyncGenerator yield token
    end

    rect rgb(255, 245, 230)
        Note over User,Alpaca: 자동매매 스케줄러 (backend lifespan → APScheduler)
        Orch->>Exec: _job() → run_trade_executor()
        Exec->>Tools: get_strategies(status=active)
        Tools->>DB: Strategy SELECT
        Exec->>Tools: evaluate_strategy(id)
        Tools->>Market: yfinance 현재가·RSI 조회
        Tools->>Domain: StrategyEvaluator.evaluate(MarketData)
        Domain-->>Tools: EvaluationResult
        Exec->>Tools: check_dca_due(id)
        Tools->>Domain: DcaScheduleChecker.is_due()
        Exec->>Tools: place_order(...)
        Tools->>Alpaca: 주문 실행 (KIS API)
        Tools->>DB: TradeLog INSERT
        Tools->>Alpaca: sync_positions()
        Tools->>DB: Holding REPLACE
    end
```

---

## REST API 엔드포인트 목록

```mermaid
graph LR
    subgraph auth["/api/auth (JWT 인증)"]
        AU1["GET /api/auth/status (공개)"]
        AU2["POST /api/auth/setup (공개, 최초 1회)"]
        AU3["POST /api/auth/login (공개, rate-limited)"]
        AU4["POST /api/auth/change-password (인증 필요)"]
        AU5["GET /api/auth/me (인증 필요)"]
    end

    subgraph portfolio["/api/portfolio"]
        P1["GET /api/portfolio<br/>holdings + P&L 스냅샷"]
        P2["POST /api/portfolio/sync<br/>KIS 포지션 동기화"]
        P3["GET /api/portfolio/holdings<br/>DB 목록 (시세 없음)"]
        P4["GET /api/portfolio/transactions<br/>KIS 체결 주문 이력"]
        P5["GET /api/portfolio/performance<br/>기간별 실현 손익 집계"]
    end

    subgraph strategies["/api/strategies"]
        S1["GET /api/strategies<br/>?status= 필터"]
        S2["POST /api/strategies<br/>생성·업데이트"]
        S3["PATCH /api/strategies/{id}/status"]
        S4["DELETE /api/strategies/{id}"]
        S5["GET /api/strategies/{id}/evaluate<br/>진입·청산 조건 평가"]
        S6["GET /api/strategies/{id}/dca-due<br/>DCA 시점 확인"]
    end

    subgraph trading["/api/trading"]
        T1["GET /api/trading/account<br/>KIS 계좌 정보"]
        T2["POST /api/trading/orders<br/>주문 실행"]
        T3["GET /api/trading/logs<br/>매매 로그"]
    end

    subgraph agent["/api/agent"]
        A1["POST /api/agent/chat/stream<br/>SSE 오케스트레이터"]
        A2["POST /api/agent/trade-executor<br/>수동 실행"]
    end

    subgraph sched["/api/scheduler + /api/settings"]
        SC1["GET /api/scheduler/status"]
        SC2["GET /api/scheduler/runs"]
        SC3["POST /api/scheduler/trigger"]
        SC4["GET /api/settings"]
        SC5["PUT /api/settings/{key}"]
    end
```

---

## 코드 레벨 검증 vs 프롬프트 지시

아래 비즈니스 규칙은 **반드시 코드로 검증**해야 한다. LLM 프롬프트 지시에만 의존하면 안 된다:

| 규칙 | 코드 검증 위치 | 이유 |
|------|--------------|------|
| 시장 개장 시간 | `tools.py::_place_order_locked()` | LLM이 시간대 계산을 틀릴 수 있음, 장 외 주문 시 실제 손실 가능 |
| max_position 초과 | `tools.py::evaluate_strategy()` + `_place_order_locked()` | DB 조회 결과에 기반한 정확한 수치 비교 필요 |
| exit_triggered 보유 전제 | `domain/services.py::StrategyEvaluator.evaluate()` | 보유 없는 공매도 방지 |
| 주문 수량/가격 유효성 | KIS API (브로커 측 검증) | 잘못된 주문은 실제 자금 손실 초래 |

**반면** 다음은 프롬프트 지시로 충분하다:
- 응답 포맷 (마크다운 테이블, 한국어 등)
- 신호 강도 판단 (signal_score 기반 매수 보류 권고)
- 분석 관점 선택 (어떤 지표를 우선 언급할지)
- 실행 이력 기반 패턴 분석

---

## 프로세스 구성

```mermaid
graph LR
    subgraph Dev["개발 환경 (make dev)"]
        BE2["uvicorn backend.main:app<br/>:8000"]
        FE2["vite dev server<br/>:5173"]
        FE2 <-->|proxy /api → :8000| BE2
    end

    subgraph Prod["프로덕션"]
        BE3["uvicorn :8000"]
        FE3["vite build → static files<br/>(nginx 또는 서빙)"]
        FE3 <-->|REST / SSE| BE3
    end

    Client --> FE2
    Client --> FE3
    Client -->|Swagger| BE2
```
