# Domain: Portfolio

## Bounded Context

보유 자산의 현황·수익 추적. **Alpaca 포지션이 SSOT(Source of Truth)**.
AI 에이전트, 대시보드, 자동매매 모두 이 컨텍스트의 도메인 객체를 통해 포트폴리오를 읽는다.

---

## Aggregate Root: `Holding`

| 속성 | 타입 | 설명 |
|------|------|------|
| `ticker` | str (Identity) | 종목 티커 (포트폴리오 내 유일) |
| `shares` | Decimal | 보유 주수 |
| `avg_price` | Decimal | 누적 매수 가중평균가 |
| `transactions` | List[Transaction] | 해당 종목의 거래 이력 (같은 Aggregate 경계) |

**불변조건 (Invariants)**

- `ticker`는 포트폴리오 내에서 유일
- `shares > 0` — 0이 되면 Holding 자체를 삭제
- `avg_price`는 누적 매수의 가중평균으로 유지

**현재 코드 위치**: `core/models.py` (ORM), `core/portfolio.py` (DAL)

---

## Entity: `Transaction`

| 속성 | 타입 | 설명 |
|------|------|------|
| `id` | int (Identity) | 자동 생성 PK |
| `ticker` | str | 연관 종목 |
| `type` | str | "buy" \| "sell" |
| `shares` | Decimal | 거래 주수 |
| `price` | Decimal | 거래 단가 |
| `timestamp` | datetime | 실행 시각 (UTC) |

**불변조건**

- 생성 후 수정 불가 (불변 감사 레코드)
- Holding과 같은 Aggregate 경계 내 — Holding을 통해서만 접근

**현재 코드 위치**: `core/models.py` (ORM), `core/portfolio.py` (`get_transactions`, `add_transaction`)

---

## Value Objects (목표)

### `PortfolioSnapshot`

특정 시점의 평가 포트폴리오 상태. 불변(immutable).

| 속성 | 타입 | 설명 |
|------|------|------|
| `as_of` | datetime | 스냅샷 기준 시각 |
| `holdings` | List[HoldingValuation] | 개별 보유 평가 |
| `total_market_value` | Money | 전체 평가금액 |
| `total_cost_basis` | Money | 전체 취득원가 |
| `total_pnl` | Money | 전체 손익 |
| `total_pnl_pct` | Decimal | 전체 손익률 (%) |

> **DDD 위반 현황**: 계산 로직이 `pages/1_Dashboard.py` 62~74줄에 누수됨 → `PortfolioValuationService`로 이동 필요

### `HoldingValuation`

개별 보유 종목의 평가 결과. 불변.

| 속성 | 타입 | 설명 |
|------|------|------|
| `ticker` | str | 종목 |
| `shares` | Decimal | 보유 주수 |
| `avg_price` | Money | 평균 취득가 |
| `current_price` | Money | 현재가 |
| `market_value` | Money | 평가금액 |
| `cost_basis` | Money | 취득원가 |
| `pnl` | Money | 손익 |
| `pnl_pct` | Decimal | 손익률 (%) |

### `Money`

금액 표현. 불변. 통화 명시.

| 속성 | 타입 | 설명 |
|------|------|------|
| `amount` | Decimal | 금액 |
| `currency` | str | 통화 코드 (기본: "USD") |

---

## Domain Services (목표)

### `PortfolioValuationService`

```python
def calculate(holdings: List[Holding], prices: Dict[str, Decimal]) -> PortfolioSnapshot
```

- 현재가를 받아 모든 Holding의 평가 결과를 계산
- `PortfolioSnapshot` + `List[HoldingValuation]` 반환
- **이동 대상**: `pages/1_Dashboard.py` 62~74줄 계산 로직

### `PositionSyncService`

```python
def sync_from_alpaca(alpaca_positions: List[AlpacaPosition]) -> List[Holding]
```

- Alpaca 포지션 목록을 도메인 Holding 목록으로 변환/동기화
- **이동 대상**: `core/alpaca_client.py` `sync_positions` + `core/portfolio.py` `rebuild_holdings_from_alpaca` 통합

---

## Repository Interfaces (목표)

### `HoldingRepository`

```python
class HoldingRepository(Protocol):
    def find_all(self) -> List[Holding]: ...
    def find_by_ticker(self, ticker: str) -> Optional[Holding]: ...
    def save(self, holding: Holding) -> None: ...
    def remove(self, ticker: str) -> None: ...
```

**현재 구현 위치**: `core/portfolio.py` (`get_holdings`, `add_holding`, `update_holding`, `delete_holding`)

### `TransactionRepository`

```python
class TransactionRepository(Protocol):
    def find_by_ticker(self, ticker: str) -> List[Transaction]: ...
    def save(self, transaction: Transaction) -> None: ...
```

**현재 구현 위치**: `core/portfolio.py` (`get_transactions`, `add_transaction`)

---

## Infrastructure Adapters (현재 위치)

| 역할 | 파일 | 설명 |
|------|------|------|
| ORM 모델 | `core/models.py` | SQLAlchemy Holding, Transaction 모델 |
| DAL | `core/portfolio.py` | SQLite CRUD 함수 (Repository 구현체) |
| Alpaca API | `core/alpaca_client.py` | 포지션 조회·동기화 |
| 현재가 조회 | `core/market.py` | Yahoo Finance via yfinance |
| DB 초기화 | `core/database.py` | SQLite 스키마 생성 |

---

## 도메인 이벤트 (목표)

| 이벤트 | 트리거 | 구독자 |
|--------|--------|--------|
| `HoldingAdded` | 새 Holding 저장 | 대시보드 캐시 무효화 |
| `HoldingRemoved` | shares=0으로 Holding 삭제 | 대시보드 캐시 무효화 |
| `PositionSynced` | Alpaca 동기화 완료 | 자동매매 전략 평가 트리거 |
