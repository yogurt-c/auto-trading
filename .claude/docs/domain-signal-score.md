# Signal Score & 전략 평가 로직

KIS AI extensions의 신호 강도 티어 설계를 기반으로 구현된 전략 평가 흐름입니다.

## 평가 흐름 개요

```
scheduler._job_body()
  → run_trade_executor()          # agent.py
    → trade-executor sub-agent
      → evaluate_strategy()       # tools.py
          → StrategyEvaluator.evaluate()  # services.py (순수 도메인 로직)
      → [application 레이어 게이트 적용]
      → place_order() (조건 통과 시)
```

## 1. 도메인 레이어: 조건 평가 (`services.py`)

### 진입 조건 목록

| 조건 키 | 내용 | 데이터 소스 |
|---------|------|------------|
| `entry_price_drop_pct` | 30일 고점 대비 하락률 (%) | `market_data.high_30d` |
| `entry_rsi_below` | RSI-14 임계값 이하 | `market_data.rsi_14` |
| `entry_bb_lower_touch` | 볼린저 하단 터치 | `market_data.bb_lower` |
| `entry_macd_hist_positive` | MACD 히스토그램 양전환 | `market_data.macd_hist` |
| `entry_disparity_below` | 이격도-20 임계값 이하 (%) | `market_data.disparity_20` |
| `entry_volume_surge` | 거래량 비율 임계값 초과 | `market_data.volume_ratio_20` |
| `entry_sma_cross` | 현재가 > SMA(20 또는 60) | `market_data.sma_20/60` |

### OR 진입 로직

각 조건은 독립적으로 평가되며 **하나라도 충족되면 `entry_triggered = True`**입니다.
이는 의도된 OR 로직이며, 실제 주문 실행 여부는 application 레이어의 `signal_score` 게이트가 추가로 결정합니다.

### signal_score 계산

```python
# services.py:350
# 분모: 데이터 가용 여부와 무관한 "전체 설정된 진입 조건 수"
configured_entry_count = sum([
    strategy.get("entry_price_drop_pct") is not None,
    strategy.get("entry_rsi_below") is not None,
    bool(strategy.get("entry_bb_lower_touch")),
    bool(strategy.get("entry_macd_hist_positive")),
    strategy.get("entry_disparity_below") is not None,
    strategy.get("entry_volume_surge") is not None,
    strategy.get("entry_sma_cross") is not None,
])
signal_score = triggered_count / configured_entry_count
```

**중요**: 분모는 시장 데이터가 실제로 수신된 조건 수가 **아니라** 전략에 설정된 조건 수입니다.
시장 데이터 미수신(상장 초기, 데이터 없음)으로 평가 불가한 조건은 미발동(0)으로 산입됩니다.

```
예시: RSI + 가격하락 + BB 3개 설정, RSI 데이터 없음
  - 가격하락 ✓, BB ✓, RSI 평가불가
  - signal_score = 2 / 3 = 0.67  (이전: 2/2 = 1.0 — 수정됨)
```

### 퇴출 조건 (보유 시에만 평가)

| 조건 키 | 내용 |
|---------|------|
| `take_profit_pct` | 현재 수익률 >= 목표 |
| `stop_loss_pct` | 현재 수익률 <= 손절 |

보유 없을 경우 `exit_triggered`는 항상 `False`.

### 30일 고점 계산 기준 (시장별 의도된 차이)

```python
# market.py:118 — 의도된 설계
if market == "KR":
    high_30d = float(highs.tail(30).max())        # 30 거래일 (약 6주)
else:
    cutoff = closes.index[-1] - pd.Timedelta(days=30)
    high_30d = float(highs[highs.index >= cutoff].max())  # 30 캘린더일 (약 3주)
```

KR은 한국 금융권 관행(거래일 기준), US는 캘린더일 기준입니다.
같은 `entry_price_drop_pct` 값도 KR 종목에서 발동 조건이 상대적으로 더 까다롭습니다.
전략 설정 시 KR/US 혼합 포트폴리오에서 임계값을 다르게 설정할 것을 권장합니다.

---

## 2. 게이트: `EntryGate` (`services.py`, Domain)

진입 신호에 비즈니스 규칙 두 가지를 적용하는 순수 함수입니다. I/O(현재 보유 평가액 조회)는
호출부가 하고 `position_value`로 주입합니다. 서버에서는 `tools.evaluate_strategy()`가 호출하며,
research 백테스트와 Android 엔진도 같은 규칙을 씁니다 (`shared/fixtures/gate` 참고).

```python
decision = EntryGate().apply(strategy, result, position_value)
# decision.entry_allowed: bool, decision.blocked_reason: str | None
```

### 게이트 1 — max_position 한도 초과

`position_value >= max_position`이면 차단. 통화 단위는 전략의 `currency` 기준 (KRW 또는 USD).

### 게이트 2 — signal_score 미달

**설정된** 진입 조건이 2개 이상이고 `signal_score < 0.5`이면 차단. 조건 수는
`count_configured_entry_conditions()`로 계산해 signal_score 분모와 같은 기준을 씁니다
(이전에는 평가된 조건 수를 세서 데이터 미수신 시 게이트가 풀리는 불일치가 있었음).

> 조건이 정확히 2개인 전략은 1개만 발동해도 0.5라 통과합니다 — 사실상 OR입니다.

### 주문 수량 — `OrderSizer`

| 방향 | 규칙 |
|------|------|
| 매수 | `min(max_position / 3, max_position - position_value, 가용현금) // 가격` (정수 주) |
| 매도 | `ceil(보유수량 * sell_ratio)` — 1주 보유 시에도 청산 가능하도록 올림 |

서버의 LLM trade-executor는 아직 자체 판단으로 수량을 정하며(스케줄러는 Android 전환 시 폐기),
`OrderSizer`는 백테스트와 Android 엔진의 기준 원본입니다.

## 3. KIS 신호 강도 티어

KIS AI extensions 기준 신호 강도 티어:

| signal_score 범위 | 주문 유형 | 설명 |
|-------------------|-----------|------|
| 0.8 ~ 1.0 | 시장가(Market) | 강한 신호 |
| 0.5 ~ 0.8 | 지정가(Limit) | 보통 신호 |
| < 0.5 | 미실행 | 신호 미달, 차단 |

현재 구현에서 주문 유형 분기는 LLM sub-agent(trade-executor)가 `signal_score`를 보고 판단합니다.
`agent.py:231` 프롬프트에 위 기준이 명시되어 있습니다.

---

## 4. 새 진입 조건 추가 시 체크리스트

진입 조건을 추가할 때 반드시 아래를 모두 수행합니다:

1. **`MarketData` VO** (`value_objects.py`) — 새 필드 추가
2. **`fetch_market_data()`** (`market.py`) — 지표 계산 및 반환
3. **`StrategyEvaluator.evaluate()`** (`services.py`) — 조건 평가 블록 추가
4. **`configured_entry_count` 합산** (`services.py:350`) — signal_score 분모에 신규 조건 포함
5. **`StrategyValidator.validate()`** (`services.py`) — 파라미터 범위 검증 추가
6. **`Strategy` ORM 컬럼** (`models.py`) — DB 컬럼 추가
7. **Alembic 마이그레이션** — 스키마 변경 적용
8. **`domain-strategy.md`** — 도메인 명세 업데이트
9. **`agent.py` 프롬프트** — trade-executor 신호 해석 안내 업데이트 (필요 시)
