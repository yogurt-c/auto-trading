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

## 2. Application 레이어: 게이트 (`tools.py:286-327`)

도메인 결과에 두 가지 비즈니스 규칙을 추가로 적용합니다.

### 게이트 1 — max_position 한도 초과

```python
if current_value >= max_position:
    result_dict["entry_triggered"] = False  # 주문 차단
```

통화 단위는 전략의 `currency` 필드 기준 (KRW 또는 USD). 불일치 시 경고 로그.

### 게이트 2 — signal_score 미달

```python
# 진입 조건이 2개 이상인 전략에만 적용
if entry_cond_count >= 2 and signal_score < 0.5:
    result_dict["entry_triggered"] = False  # 주문 차단
```

진입 조건이 1개인 전략은 `entry_triggered` 값만으로 판단 (score 게이트 생략).

---

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
