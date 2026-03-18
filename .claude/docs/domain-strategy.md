# Domain: TradingStrategy

## Bounded Context

매매 전략 규칙 정의, 조건 평가, 실행 이력 추적.
AI 에이전트가 자연어로 전략을 생성하고, 스케줄러가 주기적으로 조건을 평가해 Alpaca 주문을 실행한다.

---

## Aggregate Root: `Strategy`

| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | int (Identity) | 자동 생성 PK |
| `ticker` | str | 대상 종목 |
| `strategy_type` | str | "dca" \| "buy_dip" \| "take_profit" \| "stop_loss" |
| `status` | StrategyStatus | 전략 상태 머신 |
| `entry_condition` | EntryCondition | 진입 조건 묶음 |
| `exit_condition` | ExitCondition | 청산 조건 묶음 |
| `dca_schedule` | Optional[DcaSchedule] | DCA 전략 일정 (dca 타입만) |
| `risk_limit` | RiskLimit | 리스크 한도 |
| `trade_logs` | List[TradeLog] | 실행 이력 (같은 Aggregate 경계) |
| `created_at` | datetime | 전략 생성 시각 |

**불변조건 (Invariants)**

- `exit_condition.stop_loss_pct < exit_condition.take_profit_pct` (손절이 목표보다 낮아야 함)
- `strategy_type == "dca"` 이면 `dca_schedule` 필수
- `entry_condition.entry_price_drop_pct`은 양수 (가격 하락률이므로)
- `status` 전이: `active → paused → completed` (역방향 불가)

**현재 코드 위치**: `core/models.py` (ORM), `core/portfolio.py` (DAL)

---

## Entity: `TradeLog`

| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | int (Identity) | 자동 생성 PK |
| `strategy_id` | int | 연관 전략 ID |
| `action` | str | "buy" \| "sell" |
| `ticker` | str | 종목 티커 |
| `shares` | Decimal | 실행 주수 |
| `price` | Decimal | 실행 단가 |
| `order_id` | Optional[str] | Alpaca 주문 ID |
| `reason` | str | 실행 사유 (조건 설명) |
| `executed_at` | datetime | 실행 시각 (UTC) |

**불변조건**

- 생성 후 수정 불가 (실행 이력 불변 레코드)
- Strategy Aggregate의 자식 — `Strategy.trade_logs`를 통해서만 접근

**현재 코드 위치**: `core/models.py` (ORM), `core/portfolio.py` (`save_trade_log`, `get_trade_logs`)

---

## Value Objects (목표)

### `EntryCondition`

진입 조건 묶음. 불변(immutable).

| 속성 | 타입 | 설명 |
|------|------|------|
| `entry_price_drop_pct` | Optional[Decimal] | 30일 고점 대비 하락률 임계값 (%) |
| `entry_rsi_below` | Optional[Decimal] | 진입 RSI 임계값 (이하일 때 진입) |

> RSI 계산: 14일 Wilder's Smoothing Method

### `ExitCondition`

청산 조건 묶음. 불변.

| 속성 | 타입 | 설명 |
|------|------|------|
| `take_profit_pct` | Optional[Decimal] | 목표 수익률 (%) |
| `stop_loss_pct` | Optional[Decimal] | 손절 수익률 (%, 음수) |
| `sell_ratio` | Decimal | 청산 비율 (0.0~1.0, 기본 1.0) |

### `DcaSchedule`

DCA(Dollar-Cost Averaging) 일정. 불변. `strategy_type == "dca"`에만 사용.

| 속성 | 타입 | 설명 |
|------|------|------|
| `amount_usd` | Decimal | 회당 매수 금액 (USD) |
| `frequency_days` | int | 매수 주기 (일) |
| `last_executed_at` | Optional[datetime] | 마지막 실행 시각 |

### `RiskLimit`

리스크 한도. 불변.

| 속성 | 타입 | 설명 |
|------|------|------|
| `max_position_usd` | Optional[Decimal] | 최대 포지션 한도 (USD) |

### `StrategyStatus`

상태 머신. 허용 전이만 수행.

```
active ──→ paused ──→ completed
  └──────────────────────────→
```

| 값 | 의미 |
|----|------|
| `active` | 스케줄러가 조건 평가 중 |
| `paused` | 일시 중지 (조건 평가 건너뜀) |
| `completed` | 종료 (전략 목표 달성 또는 수동 종료) |

**불변조건**: `completed` 상태에서 다른 상태로 전이 불가

---

## Domain Services (목표)

### `StrategyEvaluator`

```python
def evaluate(
    strategy: Strategy,
    market_data: MarketData,
    current_holding: Optional[Holding]
) -> EvaluationResult
```

- **진입 평가**: 30일 고점 대비 하락률, 14일 RSI (Wilder's method)
- **청산 평가**: `take_profit_pct` / `stop_loss_pct` 대비 현재 P&L%
- `EvaluationResult`: `should_buy | should_sell | hold`, `reason: str`
- **이동 대상**: `core/tools.py` `evaluate_strategy()` 171~277줄

### `DcaScheduleChecker`

```python
def is_due(strategy: Strategy) -> bool
```

- DCA 전략의 다음 실행 시각 도래 여부 판단
- `last_executed_at + frequency_days <= now`
- **이동 대상**: `core/tools.py` `check_dca_due()` 290~331줄

### `StrategyValidator`

```python
def validate(params: Dict) -> List[ValidationWarning]
```

- 전략 파라미터 유효성 검증 (불변조건 사전 검사)
- `ValidationWarning`: `field: str`, `message: str`, `severity: "error" | "warning"`
- 검증 항목: stop_loss < take_profit, dca 타입 필수 필드, 양수 조건값 등
- **이동 대상**: `core/tools.py` `_validate_strategy_params()` 49~111줄

---

## Repository Interfaces (목표)

### `StrategyRepository`

```python
class StrategyRepository(Protocol):
    def find_active(self) -> List[Strategy]: ...
    def find_by_id(self, strategy_id: int) -> Optional[Strategy]: ...
    def save(self, strategy: Strategy) -> Strategy: ...
    def update_status(self, strategy_id: int, status: StrategyStatus) -> None: ...
    def delete(self, strategy_id: int) -> None: ...
```

**현재 구현 위치**: `core/portfolio.py` (`get_strategies`, `save_strategy`, `update_strategy_status`, `delete_strategy`)

### `TradeLogRepository`

```python
class TradeLogRepository(Protocol):
    def save(self, trade_log: TradeLog) -> None: ...
    def find_by_strategy_id(self, strategy_id: int) -> List[TradeLog]: ...
```

**현재 구현 위치**: `core/portfolio.py` (`save_trade_log`, `get_trade_logs`)

---

## Infrastructure Adapters (현재 위치)

| 역할 | 파일 | 설명 |
|------|------|------|
| ORM 모델 | `core/models.py` | SQLAlchemy Strategy, TradeLog 모델 |
| DAL | `core/portfolio.py` | SQLite CRUD 함수 (Repository 구현체) |
| 전략 평가 | `core/tools.py` | `evaluate_strategy`, `check_dca_due` (→ Domain Service 이동 대상) |
| 전략 파라미터 검증 | `core/tools.py` | `_validate_strategy_params` (→ Domain Service 이동 대상) |
| Alpaca 주문 | `core/alpaca_client.py` | `place_order` (Application Layer에서 호출) |
| 시장 데이터 | `core/market.py` | Yahoo Finance (RSI, 30일 고점 계산용) |

---

## Application Services (현재 위치 — Application Layer)

| 서비스 | 함수 | 위치 | 설명 |
|--------|------|------|------|
| AI 전략 생성 | `stream_orchestrator` | `core/agent.py` | 자연어 → Strategy 파라미터 추출 |
| 자동매매 실행 | `run_trade_executor` | `core/agent.py` | 조건 평가 → 주문 실행 |
| 스케줄러 잡 | `_job` | `pages/4_Auto_Trading.py` | 주기적 전략 평가 트리거 |

---

## 도메인 이벤트 (목표)

| 이벤트 | 트리거 | 구독자 |
|--------|--------|--------|
| `StrategyCreated` | 새 Strategy 저장 | 자동매매 페이지 목록 갱신 |
| `StrategyStatusChanged` | 상태 전이 발생 | 스케줄러 평가 대상 목록 갱신 |
| `TradeExecuted` | 주문 실행 성공 | Portfolio 도메인 Position Sync 트리거 |
| `StrategyCompleted` | status → completed | 사용자 알림 (Streamlit toast) |
