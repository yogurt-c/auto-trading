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
