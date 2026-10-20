# shared/fixtures

전략 로직의 **입력 → 기대 출력** JSON. 기준 원본은 `backend/app/domain/` + `backend/app/infrastructure/indicators.py`(indicators·evaluator·gate·sizer)와
`research/src/research/rebalance.py`(profiles·rebalance)이며, pytest와 Android Kotlin 테스트(`android/core`)가 같은 파일을 읽는다.

- 생성: `cd research && .venv/bin/python scripts/gen_fixtures.py` — 직접 수정하지 않는다
- 도메인·지표 로직을 바꾸면 **같은 커밋에서 재생성**한다 (backend CI가 불일치를 잡는다)
- 입력 시세는 결정적 합성 데이터 (KRX 원본은 재배포 금지)

## 공통 필드

| 키 | 의미 |
|----|------|
| `schema_version` | 형식 버전 (현재 1) |
| `lookback_bars` | 지표 계산에 쓰는 마지막 완결 일봉 수 (250) |
| `input` / `expected` | 카테고리별 아래 형식 |

## 카테고리

| 폴더 | input | expected | 대응 코드 |
|------|-------|----------|-----------|
| `indicators/` | `dates`, `high`, `low`, `close`, `volume` (오래된 순, 마지막 = 판단일) | `MarketData` 필드 전체 (`null` = 계산 불가) | `build_market_data` |
| `evaluator/` | `strategy`, `market_data`, `holding`(`{avg_price}` 또는 `null`) | `EvaluationResult` | `StrategyEvaluator.evaluate` |
| `gate/` | `strategy`, `result`(`entry_triggered`, `signal_score`), `position_value` | `{entry_allowed, blocked_reason}` | `EntryGate.apply` |
| `profiles/` | 없음 | 앱 성향 → `{종목코드: 비중}` | Android `Profile` (기준: `research/config/r3_profiles.yaml`·`r4_conservative.yaml`) |
| `rebalance/` | `weights`, `holdings`, `prices`(전일 종가), `cash`, `managed_codes`, `params` | `equity`, `targets`, `sells` → `holdings_after_sells`·`cash_after_sells` → `buys` | `research/src/research/rebalance.py` → Android `RebalancePlanner` |
| `sizer/` | `buy`(`max_position`, `position_value`, `price`, `available_cash`) 또는 `sell`(`shares`, `sell_ratio`) | 정수 수량 | `OrderSizer` |

## 비교 규칙 (Kotlin 포팅 시)

- `rebalance` 수량·주문 목록은 **정확히 일치** (매도는 종목코드 순, 매수는 종목코드 순으로 예수금 소진)
- 판정 필드(`entry_triggered`, `exit_triggered`, `entry_allowed`, `conditions.*.triggered`, 수량)는 **정확히 일치**
- 실수 값은 상대오차 `1e-9` 이내 (연산 순서 차이 허용). `signal_score`·`conditions`의 값은 소수 반올림된 값 그대로 비교
- 문자열(`note`, `blocked_reason`)은 참고용 — 비교하지 않는다
- RSI는 Wilder 평활: 첫 평균 = 최초 14개 변화량의 단순평균, 이후 `avg = (avg*13 + x)/14`. `avg_loss == 0`이면 `avg_gain > 0`일 때 100, 아니면 `null`
- EMA는 `adjust=False` 방식 (`ema_0 = x_0`, `ema_t = a*x_t + (1-a)*ema_{t-1}`, `a = 2/(span+1)`), 볼린저 표준편차는 모집단(ddof=0)
- ATR은 True Range의 **단순** 14일 평균 (Wilder 아님), 거래량 비율은 `오늘 거래량 / 직전 20일(오늘 제외) 평균`
- `high_30d`는 KR 기준 마지막 30개 봉의 고가 최댓값
