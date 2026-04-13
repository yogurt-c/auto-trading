# TODO LIST — KIS AI Extensions 적용

> 참고 레포: https://github.com/koreainvestment/kis-ai-extensions

---

## Part 1: 기술지표 라이브러리 확장

현재 `StrategyEvaluator`는 `entry_price_drop_pct`(30일 고점 대비 하락률)와 `entry_rsi_below`(14일 RSI) 두 가지만 지원한다.
kis-ai-extensions의 80개 기술지표를 참조해 지표 계층을 분리하고 다양한 진입 조건을 지원한다.

### 1-1. 기술지표 모듈 신규 생성

- [ ] `backend/app/infrastructure/indicators.py` 생성
  - 인터페이스 정의: `Indicator` Protocol (`compute(prices: pd.Series) -> float | None`)
  - 이동평균 계산 함수: `sma(prices, period)`, `ema(prices, period)`
  - 골든/데드크로스 판정: `golden_cross(prices, short=20, long=50) -> bool`
  - MACD 계산: `macd(prices, fast=12, slow=26, signal=9) -> tuple[float, float, float]`
  - 볼린저 밴드: `bollinger_bands(prices, period=20, std=2) -> tuple[float, float, float]`
  - 이격도: `disparity(prices, period=20) -> float`
  - 52주 신고가 여부: `is_52w_high(prices) -> bool`
  - 모멘텀 스코어: `momentum(prices, period=12) -> float`
  - ATR (변동성): `atr(high, low, close, period=14) -> float`
  - 연속 상승/하락 일수: `consecutive_up_days(prices) -> int`, `consecutive_down_days(prices) -> int`
  - 볼륨 급등 판정: `volume_surge(volumes, period=20, multiplier=2.0) -> bool`

### 1-2. MarketData 값객체 확장

- [ ] `backend/app/domain/trading_strategy/value_objects.py`의 `MarketData` 필드 추가
  - `market: Literal["KR", "US"] = "US"` — strategy.market 값을 그대로 전달
  - `sma_20: float | None = None`
  - `sma_50: float | None = None`
  - `ema_12: float | None = None`
  - `macd_line: float | None = None`
  - `macd_signal: float | None = None`
  - `bb_upper: float | None = None`
  - `bb_lower: float | None = None`
  - `disparity_20: float | None = None`
  - `momentum_12: float | None = None`
  - `atr_14: float | None = None`
  - `volume_surge: bool | None = None`
  - `is_52w_high: bool | None = None`

### 1-3. 시장 데이터 수집 확장

- [ ] `backend/app/infrastructure/market.py`에 지표 데이터 수집 함수 추가
  - `fetch_market_data(ticker: str, market: Literal["KR", "US"], currency: str) -> MarketData`
    - `market` 값으로 yfinance 티커 포맷 결정: KR → `{ticker}.KS`, US → `{ticker}`
    - yfinance로 1년치 일봉 OHLCV 조회
    - 30일 고점: KR은 `.tail(30)` (거래일 기준), US는 캘린더일 기준 날짜 필터
    - `indicators.py` 함수들 호출해 MarketData 필드 채움
    - 기존 인라인 RSI 계산 코드 제거 후 `calc_rsi()` 호출로 교체
  - 기존 `get_current_prices()` 함수는 유지 (포트폴리오 가격 조회용)

### 1-4. EntryCondition 값객체 확장

- [ ] `backend/app/domain/trading_strategy/value_objects.py`에 신규 진입 조건 필드 추가
  - `entry_golden_cross: bool | None = None` — 골든크로스 발생 시 진입
  - `entry_macd_cross: bool | None = None` — MACD 시그널 상향돌파 시 진입
  - `entry_bb_below_lower: bool | None = None` — 볼린저 하단 이탈 시 진입
  - `entry_disparity_below: float | None = None` — 이격도 임계값 이하 시 진입
  - `entry_momentum_above: float | None = None` — 모멘텀 스코어 임계값 이상 시 진입
  - `entry_52w_high: bool | None = None` — 52주 신고가 돌파 시 진입
  - `entry_volume_surge: bool | None = None` — 거래량 급증 시 진입

### 1-5. StrategyEvaluator 확장

- [ ] `backend/app/domain/trading_strategy/services.py`의 `StrategyEvaluator.evaluate()` 수정
  - 새로운 진입 조건 7가지 평가 블록 추가
  - 조건별 평가 결과를 `conditions` dict에 포함
  - `EvaluationResult` 반환은 기존 인터페이스 유지

### 1-6. 신호 강도 스코어링 도입

- [ ] `EvaluationResult`에 `signal_score: float` 필드 추가 (0.0 ~ 1.0)
  - 발동된 진입 조건 수 / 전체 활성 진입 조건 수 = 기본 스코어
  - 가중치 적용 가능하도록 `_condition_weights` dict 설계
- [ ] `StrategyEvaluator`에서 `signal_score` 계산 로직 추가

### 1-7. 전략 파라미터 검증 확장

- [ ] `StrategyValidator.validate()`에 신규 조건 검증 추가
  - `entry_disparity_below` 유효 범위 검증
  - `entry_momentum_above` 유효 범위 검증
  - 진입 조건이 하나도 설정되지 않은 경우 WARNING 추가

### 1-8. DB 스키마 마이그레이션

- [ ] `backend/alembic/versions/`에 마이그레이션 파일 추가
  - `strategies` 테이블에 `market` 컬럼 추가: `"KR" | "US"`, NOT NULL, 기본값 `"US"`
  - `strategies` 테이블에 신규 진입 조건 컬럼 추가 (nullable)

### 1-9. API 레이어 연동

- [ ] `backend/app/api/strategies.py` 요청/응답 스키마에 신규 필드 반영
- [ ] 프론트엔드 `frontend/src/api/types.ts`의 `Strategy` 타입에 신규 필드 추가

### 1-10. 프리셋 전략 API 추가

- [ ] `GET /api/strategies/presets` 엔드포인트 추가
  - 10개 프리셋 메타데이터 반환 (이름, 설명, 권장 파라미터, 위험도)
  - 프리셋 목록 예시:
    | 프리셋 | 핵심 조건 | 위험도 |
    |--------|-----------|--------|
    | 골든크로스 | SMA 20/50 골든크로스 | 중간 |
    | 모멘텀 | 12일 모멘텀 양수 | 중간 |
    | 52주 신고가 | 신고가 돌파 | 높음 |
    | 이격도 반등 | 이격도 95 이하 | 낮음 |
    | 볼린저 하단 | BB 하단 이탈 | 낮음 |
    | MACD 크로스 | MACD 시그널 상향돌파 | 중간 |
    | 연속 하락 반등 | 3일 연속 하락 | 낮음 |
    | 변동성 확장 | ATR 급증 | 높음 |
    | 거래량 급증 | 거래량 20일 평균 2배 | 중간 |
    | DCA 기본 | 정액 주기 매수 | 낮음 |

### 1-11. 프론트엔드 — AutoTrading UI 수정

- [ ] `frontend/src/pages/AutoTrading.tsx` 전략 생성 폼에 신규 조건 추가
  - "고급 진입 조건" 섹션 분리 (기존 조건 / 기술지표 조건)
  - 프리셋 드롭다운 추가 → 선택 시 권장 파라미터 자동 입력
  - 신호 강도 게이지 표시 (EvaluationResult.signal_score 시각화)

### 1-12. 테스트

- [ ] `backend/tests/domain/test_indicators.py` 작성
  - 각 지표 함수에 대한 단위 테스트 (알려진 입력값 → 예상 출력값)
  - 엣지 케이스: 빈 시리즈, NaN 포함 데이터
- [ ] `backend/tests/domain/test_strategy_evaluator.py` 신규 조건 테스트 추가
  - 각 진입 조건별 발동/미발동 시나리오
  - `signal_score` 계산 정확도 검증

---

## Part 2: 백테스팅 엔진 통합

현재 전략은 현재가 기준 조건 평가만 가능하며 역사적 성과 검증 수단이 없다.
kis-ai-extensions의 QuantConnect Lean 기반 백테스팅을 통합해 전략 신뢰도를 높인다.

### 전제 조건

- Docker Desktop 설치 필요
- Python 3.11+
- QuantConnect Lean Docker 이미지: `quantconnect/lean:latest`

---

### 2-1. 백테스팅 도메인 모델 설계

- [ ] `backend/app/domain/backtesting/` 패키지 신규 생성
  - `__init__.py`
  - `value_objects.py`: `BacktestConfig`, `BacktestResult` 값객체 정의
    ```python
    class BacktestConfig(BaseModel):
        strategy_id: int
        ticker: str
        start_date: date
        end_date: date
        initial_capital: float = 10_000_000  # KRW
        strategy_params: dict

    class BacktestResult(BaseModel):
        strategy_id: int
        status: Literal["pending", "running", "completed", "failed"]
        cagr: float | None = None
        sharpe_ratio: float | None = None
        max_drawdown: float | None = None
        win_rate: float | None = None
        total_trades: int | None = None
        report_path: str | None = None
        error_message: str | None = None
        created_at: datetime
        completed_at: datetime | None = None
    ```

### 2-2. Lean 알고리즘 템플릿 생성

- [ ] `backend/backtesting/` 디렉터리 신규 생성
  - `templates/base_algorithm.py` — QuantConnect Lean Python 알고리즘 기본 틀
  - `templates/entry_exit_algorithm.py` — 진입/청산 조건 기반 알고리즘 (EntryCondition, ExitCondition 파라미터 주입)
  - `templates/dca_algorithm.py` — DCA 전략 알고리즘
  - `lean.json` — Lean 설정 파일 템플릿 (기간, 자본금 등)

### 2-3. 백테스팅 Application Service 구현

- [ ] `backend/app/application/backtester.py` 신규 생성
  - `BacktestService` 클래스
    - `run_async(config: BacktestConfig) -> str` — 백테스트 비동기 실행, job_id 반환
    - `get_status(job_id: str) -> BacktestResult` — 실행 상태 조회
    - `get_report_html(job_id: str) -> str` — HTML 리포트 반환
  - 내부 구현:
    - 전략 파라미터를 Lean 알고리즘 템플릿에 주입 (Jinja2 렌더링)
    - Docker SDK로 `quantconnect/lean` 컨테이너 실행
    - 컨테이너 stdout/stderr 수집해 실행 상태 업데이트
    - 완료 후 결과 JSON 파싱해 `BacktestResult` 생성

### 2-4. DB 스키마 — backtest_results 테이블

- [ ] `backend/app/infrastructure/models.py`에 `BacktestResultORM` 모델 추가
  - `id`, `strategy_id`, `status`, `cagr`, `sharpe_ratio`, `max_drawdown`,
    `win_rate`, `total_trades`, `report_path`, `error_message`,
    `created_at`, `completed_at`
- [ ] Alembic 마이그레이션 파일 추가 (`create_backtest_results_table`)

### 2-5. Repository 구현

- [ ] `backend/app/infrastructure/repository.py`에 `BacktestResultRepository` 추가
  - `save(result: BacktestResult) -> BacktestResult`
  - `find_by_id(backtest_id: int) -> BacktestResult | None`
  - `find_by_strategy_id(strategy_id: int) -> list[BacktestResult]`
  - `update_status(backtest_id: int, result: BacktestResult) -> None`

### 2-6. API 엔드포인트 추가

- [ ] `backend/app/api/` 에 `backtesting.py` 신규 생성 (또는 `strategies.py`에 추가)
  - `POST /api/strategies/{strategy_id}/backtest` — 백테스트 실행 요청
    - Request: `{ start_date, end_date, initial_capital }`
    - Response: `{ backtest_id, status: "pending" }`
  - `GET /api/backtests/{backtest_id}` — 실행 상태 및 결과 조회
  - `GET /api/backtests/{backtest_id}/report` — HTML 리포트 반환
  - `GET /api/strategies/{strategy_id}/backtests` — 전략의 전체 백테스트 목록

### 2-7. AI 에이전트 도구 연동

- [ ] `backend/app/application/tools.py`에 백테스팅 도구 추가
  - `run_backtest(strategy_id, start_date, end_date)` — 에이전트가 자연어로 백테스트 실행
  - `get_backtest_result(backtest_id)` — 결과 요약 반환
  - 에이전트 시스템 프롬프트에 백테스팅 가이드 추가

### 2-8. 프론트엔드 — 백테스트 UI

- [ ] `frontend/src/api/types.ts`에 `BacktestResult`, `BacktestConfig` 타입 추가
- [ ] `frontend/src/pages/AutoTrading.tsx` 전략 카드에 "백테스트 실행" 버튼 추가
  - 날짜 범위 피커 (start_date, end_date)
  - 실행 상태 폴링 (pending → running → completed)
  - 완료 시 핵심 지표 인라인 표시: CAGR, Sharpe, MDD, Win Rate
- [ ] `frontend/src/pages/` 에 `Backtesting.tsx` 페이지 신규 생성 (선택)
  - 전략별 백테스트 이력 목록
  - HTML 리포트 iframe 임베드
  - 파라미터별 성과 비교 차트

### 2-9. 파라미터 최적화 (옵션)

- [ ] `backend/app/application/backtester.py`에 `optimize()` 메서드 추가
  - Grid search 방식으로 파라미터 조합 순회
  - Sharpe Ratio 최대화 기준으로 최적 파라미터 반환
  - 최적화 결과를 DB에 저장하고 에이전트 응답에 포함

### 2-10. 테스트

- [ ] `backend/tests/application/test_backtester.py` 작성
  - Docker 없이 실행 가능한 단위 테스트 (MockDocker)
  - 알고리즘 템플릿 렌더링 정확도 검증
  - `BacktestResult` 파싱 로직 검증
- [ ] `backend/tests/domain/test_backtest_value_objects.py`
  - `BacktestConfig` 유효성 검증 (날짜 범위, 자본금 최솟값)
  - `BacktestResult` 불변 조건 검증

---

## Part 3: 전략 수립 고도화 (kis-strategy-builder 참조)

kis-ai-extensions `shared/skills/kis-strategy-builder/SKILL.md` 기반.
현재 OR-only 단일 로직과 8개 지표의 한계를 극복한다.

### 3-1. 진입 조건 AND/OR 로직 선택 — 최우선

- [ ] `strategies` 테이블에 `condition_logic: str = "OR"` 컬럼 추가
  - Alembic 마이그레이션 `003_add_condition_logic.py`
  - `backend/app/infrastructure/models.py` Strategy 모델 반영
- [ ] `StrategyEvaluator.evaluate()` 분기 처리
  - `condition_logic == "AND"` → 모든 활성 진입 조건이 충족될 때만 `entry_triggered = True`
  - `condition_logic == "OR"` → 기존 동작 유지 (하나라도 충족)
  - `signal_score` 계산 방식은 logic에 무관하게 동일하게 유지
- [ ] `StrategyValidator` — AND 로직에서 진입 조건이 1개만 있을 때 WARNING 추가
- [ ] `StrategyCreate` API 스키마에 `condition_logic: str = "OR"` 추가
- [ ] `STRATEGY_TOOLS` input_schema에 `condition_logic` 파라미터 설명 추가
- [ ] 프론트엔드 `AutoTrading.tsx` 진입 조건 섹션에 AND/OR 토글 추가
- [ ] 테스트: AND 로직 발동/미발동 시나리오, OR와의 동작 차이 검증

### 3-2. 추가 기술지표 — ADX, Stochastic, OBV, CCI, Williams %R

- [ ] `backend/app/infrastructure/indicators.py` 함수 추가
  - `calc_adx(highs, lows, closes, period=14) -> float | None` — 추세 강도 (0~100)
  - `calc_stochastic(highs, lows, closes, k=14, d=3) -> tuple[float|None, float|None]` — %K, %D
  - `calc_obv(closes, volumes) -> float | None` — 거래량 모멘텀 (절대값보다 방향성 사용)
  - `calc_cci(highs, lows, closes, period=20) -> float | None` — 평균 대비 편차
  - `calc_williams_r(highs, lows, closes, period=14) -> float | None` — -100~0 범위
  - `calc_consecutive(closes) -> int` — 양수=연속 상승일, 음수=연속 하락일

- [ ] `MarketData` 값객체에 필드 추가
  - `adx_14: float | None = None`
  - `stoch_k: float | None = None`
  - `stoch_d: float | None = None`
  - `obv: float | None = None`
  - `cci_20: float | None = None`
  - `williams_r: float | None = None`
  - `consecutive_days: int | None = None`

- [ ] `fetch_market_data()` 에서 신규 지표 계산 및 MarketData 채우기

- [ ] `StrategyEvaluator` 진입 조건 추가
  | 파라미터 | 조건 | 설명 |
  |----------|------|------|
  | `entry_adx_above: float` | `adx_14 >= threshold` | 추세 강도 임계값 이상 (예: 25.0) |
  | `entry_stoch_oversold: float` | `stoch_k <= threshold` | 스토캐스틱 과매도 (예: 20.0) |
  | `entry_cci_oversold: float` | `cci_20 <= threshold` | CCI 과매도 (예: -100.0) |
  | `entry_williams_oversold: float` | `williams_r <= threshold` | Williams %R 과매도 (예: -80.0) |
  | `entry_consecutive_down: int` | `consecutive_days <= -N` | N일 연속 하락 (예: -3) |

- [ ] `strategies` 테이블에 신규 컬럼 추가 (Alembic `004_add_advanced_indicators.py`)
- [ ] `StrategyValidator` 신규 파라미터 범위 검증 추가
  - `entry_adx_above`: 0~100 범위
  - `entry_stoch_oversold`: 0~100 범위
  - `entry_cci_oversold`: 일반적으로 -200~0
  - `entry_williams_oversold`: -100~0 범위
  - `entry_consecutive_down`: 음수여야 함
- [ ] `StrategyCreate`, `STRATEGY_TOOLS` 스키마 반영
- [ ] 프리셋 추가: ADX 추세 필터, 스토캐스틱 과매도, N일 연속 하락 반등
- [ ] 테스트: 각 조건 발동/미발동 + `calc_*` 함수 단위 테스트

### 3-3. 캔들스틱 패턴 인식 (66개)

> ⚠️ 별도 구현 규모. Part 3 중 가장 복잡.

- [ ] `backend/app/infrastructure/candle_patterns.py` 신규 생성
  - `pandas_ta` 또는 `TA-Lib` 기반 패턴 인식 (의존성 결정 필요)
  - 주요 패턴 우선 구현: `hammer`, `doji`, `engulfing`, `morning_star`, `shooting_star`
  - `detect_patterns(opens, highs, lows, closes) -> list[str]` — 현재 캔들에서 감지된 패턴 목록 반환

- [ ] `MarketData`에 `candle_patterns: list[str] = []` 필드 추가

- [ ] `StrategyEvaluator`에 `entry_candle_pattern: str | None` 진입 조건 추가
  - `entry_candle_pattern`이 `market_data.candle_patterns`에 포함되면 발동

- [ ] DB, API, 프론트엔드 연동

- [ ] 테스트: 알려진 OHLC 시퀀스로 패턴 감지 검증

---

## 진행 순서 (권장)

```
Part 1 (기술지표) — 완료 ✓

Part 2 (백테스팅)
  2-1 도메인 모델 설계
  2-2 Lean 템플릿 생성
  2-3 BacktestService 구현
  2-4 DB 스키마
  2-5 Repository
  2-6 API 엔드포인트
  2-7 에이전트 도구 연동
  2-8 프론트엔드 UI
  2-9 파라미터 최적화 (옵션)
  2-10 테스트

Part 3 (전략 수립 고도화)
  3-1 AND/OR 조건 로직 ← 최우선 (작업 범위 작음)
  3-2 추가 지표 (ADX, Stochastic, OBV, CCI, Williams %R, Consecutive)
  3-3 캔들스틱 패턴 (별도 과제)
```
