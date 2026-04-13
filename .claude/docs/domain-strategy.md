# Domain: TradingStrategy

## Bounded Context

매매 전략 규칙 정의, 조건 평가, 실행 이력 추적.
AI 에이전트가 자연어로 전략을 생성하고, 스케줄러가 주기적으로 조건을 평가해 KIS 주문을 실행한다.

---

## Aggregate Root: `Strategy`

| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | int (Identity) | 자동 생성 PK |
| `ticker` | str | 대상 종목 |
| `strategy_type` | str | "dca" \| "momentum" \| "value" \| "stop_loss" \| "take_profit" \| "custom" |
| `status` | StrategyStatus | 전략 상태 머신 |
| `entry_condition` | EntryCondition | 진입 조건 묶음 |
| `exit_condition` | ExitCondition | 청산 조건 묶음 |
| `dca_schedule` | Optional[DcaSchedule] | DCA 전략 일정 (dca 타입만) |
| `risk_limit` | RiskLimit | 리스크 한도 |
| `trade_logs` | List[TradeLog] | 실행 이력 (같은 Aggregate 경계) |
| `created_at` | datetime | 전략 생성 시각 |

**불변조건 (Invariants)**

- `exit_condition.stop_loss_pct < exit_condition.take_profit_pct` (손절이 목표보다 낮아야 함)
- `strategy_type == "dca"` 이면 `dca_amount` + `dca_frequency_days` 필수
- `strategy_type != "dca"` 이면 진입 조건(EntryCondition) 최소 1개 필수
- `entry_condition.entry_price_drop_pct`은 **음수** (30일 고점 대비 하락률, 예: -5.0)
- `entry_condition.entry_disparity_below`은 **음수** (이격도 과매도 임계값, 예: -5.0)
- `entry_condition.entry_volume_surge`은 **1.0 초과** (평균 거래량 배수)
- `entry_condition.entry_sma_cross`은 **20 또는 60** 만 허용
- `dca_amount ≤ max_position` (DCA 1회 금액이 포지션 한도 이하)
- `status` 전이: `active → paused → completed` (역방향 불가)

**현재 코드 위치**: `backend/app/infrastructure/models.py` (ORM), `backend/app/infrastructure/repository.py` (DAL)

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
| `broker_order_id` | Optional[str] | KIS 주문 ID |
| `reason` | str | 실행 사유 (조건 설명) |
| `executed_at` | datetime | 실행 시각 (UTC) |

**불변조건**

- 생성 후 수정 불가 (실행 이력 불변 레코드)
- Strategy Aggregate의 자식 — `Strategy.trade_logs`를 통해서만 접근

**현재 코드 위치**: `backend/app/infrastructure/models.py` (ORM), `backend/app/infrastructure/repository.py` (`save_trade_log`, `get_trade_logs`)

---

## Value Objects (목표)

### `EntryCondition`

진입 조건 묶음. 불변(immutable). OR 로직 — 하나라도 발동되면 진입 신호.

| 속성 | 타입 | 설명 |
|------|------|------|
| `entry_price_drop_pct` | Optional[float] | 30일 고점 대비 하락률 임계값 (%, 음수, 예: -5.0) |
| `entry_rsi_below` | Optional[float] | 진입 RSI 임계값 (이하일 때 진입, 예: 30.0) |
| `entry_bb_lower_touch` | Optional[bool] | 볼린저 밴드 하단 이탈 시 진입 (`current_price ≤ bb_lower`) |
| `entry_macd_hist_positive` | Optional[bool] | MACD 히스토그램 양전환 시 진입 (`macd_hist > 0`) |
| `entry_disparity_below` | Optional[float] | 이격도 임계값 이하 시 진입 (음수, 예: -5.0) |
| `entry_volume_surge` | Optional[float] | 거래량 급등 비율 임계값 이상 시 진입 (1.0 초과, 예: 2.0 = 평균의 2배) |
| `entry_sma_cross` | Optional[int] | 현재가가 SMA(N)일 위일 때 진입 (20 또는 60 지원) |

> RSI 계산: 14일 Wilder's Smoothing Method  
> 이격도(Disparity): `(current_price / SMA_20 - 1) × 100`  
> 거래량 비율: `current_volume / avg_volume(20일)`

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
| `amount` | Decimal | 회당 매수 금액 (currency 단위: KRW 또는 USD) |
| `frequency_days` | int | 매수 주기 (일) |
| `last_executed_at` | Optional[datetime] | 마지막 실행 시각 |

### `RiskLimit`

리스크 한도. 불변.

| 속성 | 타입 | 설명 |
|------|------|------|
| `max_position` | Optional[Decimal] | 최대 포지션 한도 (currency 단위: KRW 또는 USD) |

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
    strategy: dict,
    market_data: MarketData,
    current_holding: dict | None,
) -> EvaluationResult
```

- **진입 평가 (OR 로직)**: 아래 7가지 조건 중 하나라도 충족되면 `entry_triggered = True`
  - `entry_price_drop_pct`: 30일 고점 대비 하락률 ≤ 임계값
  - `entry_rsi_below`: 14일 RSI ≤ 임계값 (Wilder's method)
  - `entry_bb_lower_touch`: 현재가 ≤ 볼린저 밴드 하단
  - `entry_macd_hist_positive`: MACD 히스토그램 > 0
  - `entry_disparity_below`: 이격도(20일) ≤ 임계값
  - `entry_volume_surge`: 거래량 비율(20일) ≥ 임계값
  - `entry_sma_cross`: 현재가 > SMA(N)일
- **청산 평가**: `take_profit_pct` / `stop_loss_pct` 대비 현재 P&L%
- **`EvaluationResult`**:
  - `entry_triggered: bool`, `exit_triggered: bool`
  - `conditions: dict` — 각 조건별 상세 (reference, current, threshold, triggered)
  - `signal_score: float | None` — 발동 진입 조건 수 / 전체 활성 진입 조건 수 (0.0 ~ 1.0)
  - `holding_avg_price: float | None`, `current_pnl_pct: float | None`
- **현재 위치**: `backend/app/domain/trading_strategy/services.py::StrategyEvaluator.evaluate()`

### `DcaScheduleChecker`

```python
def is_due(strategy: dict, now: datetime | None = None) -> dict
```

- DCA 전략의 다음 실행 시각 도래 여부 판단
- `days_since_last >= dca_frequency_days` → `is_due: True`
- **현재 위치**: `backend/app/domain/trading_strategy/services.py::DcaScheduleChecker.is_due()`

### `StrategyValidator`

```python
def validate(strategy_type, entry_price_drop_pct, entry_rsi_below, ...) -> list[ValidationWarning]
```

- 전략 파라미터 유효성 검증 (불변조건 사전 검사)
- `ValidationWarning`: `message: str`, `severity: ValidationSeverity` (`WARNING` | `ERROR`)
- ERROR는 저장 차단, WARNING은 저장은 허용하되 사용자에게 안내

| 검증 항목 | Severity | 조건 |
|-----------|----------|------|
| `entry_price_drop_pct > 0` | WARNING | 음수여야 함 (예: -5.0) |
| `entry_rsi_below` 범위 벗어남 | WARNING | 0 초과 100 미만이어야 함 |
| `\|stop_loss_pct\| < \|entry_price_drop_pct\|` | WARNING | 진입 즉시 손절 위험 |
| `entry_disparity_below > 0` | WARNING | 음수여야 함 (예: -5.0) |
| `entry_volume_surge ≤ 1.0` | WARNING | 1.0 초과여야 함 |
| `stop_loss_pct ≥ take_profit_pct` | **ERROR** | 손절이 익절 이상이면 동시 발동 |
| `sell_ratio` 범위 벗어남 | **ERROR** | 0 초과 1 이하이어야 함 |
| `dca_frequency_days ≤ 0` | **ERROR** | 양의 정수여야 함 |
| `dca_amount > max_position` | **ERROR** | 1회 금액이 포지션 한도 초과 |
| DCA 전략에 `dca_amount` 없음 | **ERROR** | DCA 필수 파라미터 |
| DCA 전략에 `dca_frequency_days` 없음 | **ERROR** | DCA 필수 파라미터 |
| `entry_sma_cross` not in (20, 60) | **ERROR** | 20 또는 60만 지원 |
| 진입 조건 모두 None (non-DCA) | **ERROR** | 최소 1개 entry 조건 필수 |

- **현재 위치**: `backend/app/domain/trading_strategy/services.py` `StrategyValidator.validate()`

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

**현재 구현 위치**: `backend/app/infrastructure/repository.py` (`get_strategies`, `save_strategy`, `update_strategy_status`, `delete_strategy`)

### `TradeLogRepository`

```python
class TradeLogRepository(Protocol):
    def save(self, trade_log: TradeLog) -> None: ...
    def find_by_strategy_id(self, strategy_id: int) -> List[TradeLog]: ...
```

**현재 구현 위치**: `backend/app/infrastructure/repository.py` (`save_trade_log`, `get_trade_logs`)

---

## Infrastructure Adapters (현재 위치)

| 역할 | 파일 | 설명 |
|------|------|------|
| ORM 모델 | `backend/app/infrastructure/models.py` | SQLAlchemy Strategy, TradeLog 모델 |
| DAL | `backend/app/infrastructure/repository.py` | SQLite CRUD 함수 (Repository 구현체) |
| 전략 평가 | `backend/app/application/tools.py` | `evaluate_strategy`, `check_dca_due` → Domain Service 위임 |
| 전략 파라미터 검증 | `backend/app/application/tools.py` | `_validate_strategy_params` → Domain Service 위임 |
| KIS 주문 | `backend/app/infrastructure/kis_client.py` | `place_order` (국내/해외 자동 분기) |
| 시장 데이터 | `backend/app/infrastructure/market.py` | Yahoo Finance (RSI, 30일 고점, 기술지표) |

---

## Application Services (현재 위치 — Application Layer)

| 서비스 | 함수 | 위치 | 설명 |
|--------|------|------|------|
| AI 전략 생성 | `stream_orchestrator` | `backend/app/application/agent.py` | 자연어 → Strategy 파라미터 추출 (strategy-advisor 서브에이전트) |
| 자동매매 실행 | `run_trade_executor` | `backend/app/application/agent.py` | 조건 평가 → 주문 실행 (trade-executor 서브에이전트) |
| 스케줄러 잡 | `_job` | `backend/app/application/scheduler.py` | 주기적 전략 평가 트리거 (APScheduler) |

---

## 도메인 이벤트 (목표)

| 이벤트 | 트리거 | 구독자 |
|--------|--------|--------|
| `StrategyCreated` | 새 Strategy 저장 | 자동매매 페이지 목록 갱신 |
| `StrategyStatusChanged` | 상태 전이 발생 | 스케줄러 평가 대상 목록 갱신 |
| `TradeExecuted` | 주문 실행 성공 | Portfolio 도메인 Position Sync 트리거 |
| `StrategyCompleted` | status → completed | 사용자 알림 (Streamlit toast) |
