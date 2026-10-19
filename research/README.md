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
