# research — P0 백테스트

현재 전략(`StrategyEvaluator`)에 기준 전략 대비 우위가 있는지 백테스트로 검증한다.

- `backend`를 `pip install -e`로 설치해 도메인·지표 코드를 **그대로 호출만** 한다. backend 코드는 여기서 고치지 않는다.
- 원본 시세 데이터(`research/data/`)는 KRX OpenAPI 약관상 재배포 금지라 커밋하지 않는다.

## 설치·실행

```bash
make research-install   # research/.venv 생성, backend + research 설치
cp research/.env.example research/.env   # KRX_AUTH_KEY, DART_API_KEY 입력
make research-test
```

## 사전 등록 (`config/`)

백테스트 실행 전에 커밋한다. 결과를 본 뒤 바꾸지 않는다.

| 파일 | 내용 |
|------|------|
| `periods.yaml` | 학습 2012–2019 / 검증 2020-01 – 2026-09 (검증은 최종 후보로 1회만) |
| `costs.yaml` | 수수료·날짜별 증권거래세·슬리피지·배당세 |
| `universe.yaml` | 분기말 KOSPI 시총 상위 50 (우선주·스팩·리츠 제외), 시점별 |
| `strategy.yaml` | S0 프리셋(현 DB 전략 중앙값), 튜닝 격자 36개, 실행 모델, S1·S2 필터 |
| `criteria.yaml` | 기준 전략, 학습 게이트, 필터 채택, 검증 통과 기준 P1–P7 |

## 데이터 (`scripts/fetch_data.py`)

| 출처 | 용도 | 비고 |
|------|------|------|
| KRX OpenAPI `sto/stk_bydd_trd` | KOSPI 전 종목 일별 시세·시총 | 날짜별 스냅샷이라 상장폐지 종목 포함. 수정주가는 `기준가 = 종가 - 전일대비`로 복원 |
| KRX OpenAPI `idx/kospi_dd_trd` | 코스피 200 (국면 필터) | |
| DART OpenAPI | 공시 목록(거부권 집계), 연간 주당 배당금 | 접수일 다음 거래일부터 반영 |
| yfinance `069500.KS` | KODEX 200 기준 전략 | 단일 ETF라 생존 편향 없음 |

KRX는 [openapi.krx.co.kr](https://openapi.krx.co.kr)에서 인증키 발급 후 **서비스별 이용신청**이 따로 필요하다:
`유가증권 일별매매정보`, `KOSPI 시리즈 일별시세정보`.

```bash
.venv/bin/python scripts/fetch_data.py krx    # 약 8,700회 호출 (한도 10,000/일), 중단 시 재실행하면 이어받음
.venv/bin/python scripts/fetch_data.py panel  # 패널·수정계수·유니버스·지수
.venv/bin/python scripts/fetch_data.py dart
.venv/bin/python scripts/fetch_data.py bench
```

## 실행 (`scripts/run_backtest.py`)

```bash
.venv/bin/python scripts/run_backtest.py train  # 첫 실행 시 MarketData 사전 계산 (병렬, 수 분)
.venv/bin/python scripts/run_backtest.py test   # 학습 게이트 통과 시에만, 단 1회
```

학습 단계 (`pipeline.run_train`):
1. 기준 전략 B1·B2·B3, 비교 대상 = B1·B3 중 Sharpe 높은 쪽
2. S0(프리셋) → S1(국면 필터) → S2(공시 거부권)를 하나씩 붙여 채택 규칙으로 판정
3. 채택된 필터 위에서 튜닝 격자 36개 → 학습 Sharpe 최고 조합
4. 최종 후보 = S 계열 vs 튜닝 계열 중 학습 Sharpe가 높은 쪽 (튜닝이면 P7 값 기록)
5. 학습 게이트 T1 불통과 시 검증 구간을 쓰지 않고 지수 정기 매수로 결론

검증 단계는 실행 직전에 `reports/TEST_RUN.lock`을 만들고, `config/`에 커밋되지 않은 변경이 있으면 거부한다.
결과는 `reports/*_report.json`과 `test_equity.csv` (커밋 대상 — 원본 시세는 포함하지 않음).

## R2 — 2차 후보 전략 (`config/r2_*.yaml`, `src/research/r2.py`)

P0 결론(현재 전략 우위 없음) 이후, 수익 개선 후보 4개를 같은 원칙(사전 등록 → 학습 → 검증 1회)으로 비교한다. 튜닝 없음.

| 후보 | 규칙 | 실행 |
|------|------|------|
| A 레버리지+추세 | 국내 2배·미국 2배 50:50, 신호 지수 < SMA200이면 해당 절반을 국고채3년으로 | `rotation.run_rotation` |
| B 듀얼 모멘텀 | 매월 말 KODEX 200·미국 S&P500 중 12개월 수익률 최고가 채권보다 높으면 그 자산, 아니면 채권 | `rotation.run_rotation` |
| C 단기 모멘텀 | 시총 상위 100 중 160일 수익률 상위 4종목, 5거래일마다 교체 | `engine.Engine(MomentumSpec)` |
| D 변동성 돌파 | KODEX 레버리지, 시가 + 0.5 x 전일 범위 돌파 시 매수, 다음 날 시가 매도 | `rotation.run_breakout` |

- 기준: B1(KODEX 200 보유), B4(KODEX 200·미국 S&P500 50:50 월 리밸런싱). 게이트 T1(Sharpe)·T2(CAGR) 모두 기준 초과.
- 국내 ETF는 yfinance 실제 시세, 미국 ETF는 S&P500 총수익 지수 x 원/달러(FRED)로 국내 상장 환노출 ETF를 합성한다
  (한국 거래일 d에는 d 이전 미국 종가만 사용). 해외지수·채권 ETF는 이익 난 매도마다 15.4% 과세.

```bash
.venv/bin/python scripts/run_r2.py train
.venv/bin/python scripts/run_r2.py test   # 게이트 통과 후보가 있을 때만, 단 1회
```
