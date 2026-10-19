# CLAUDE.md

AI-powered financial portfolio management tool — monitors holdings, runs automated trading strategies via KIS (Korea Investment & Securities), and provides a Claude AI agent for natural language interaction.

## Layout

- `backend/` · `frontend/` — 기존 서버·웹 (Android 전환 후 폐기 예정)
- `research/` — P0 백테스트. backend를 `pip install -e`로 설치해 호출만 하며, backend 코드를 고치지 않는다
- `shared/fixtures/` — 입력 → 기대 신호 JSON. pytest와 Kotlin 테스트가 함께 읽는다

## Rules

- `frontend/pages/` must only use `frontend.api_client` — never import `backend/` directly
- KIS is configured for **Paper Trading** (모의투자, safe for testing)
- 구현 완료 후 커밋 전에 반드시 [checklist-development.md](.claude/docs/checklist-development.md)의 모든 항목을 확인하고, 해당 항목을 스스로 실행(테스트 실행·빌드·문서 업데이트 등)한다 — 사용자가 요청하지 않아도 자동으로 수행한다
- dict key로 ORM 필드에 접근할 때 반드시 `backend/app/infrastructure/models.py`의 컬럼명을 확인한다 — 추측 금지 (예: Holding은 `shares`이지 `quantity`가 아님)
- 포지션 한도·시장 시간·주문 가능 여부 등 비즈니스 불변조건은 반드시 **코드 레벨**에서 검증한다 — LLM 프롬프트 지시에만 의존하지 않는다
- 도메인 Value Object에 새 필드를 추가하면, 그 필드를 **소비하는 로직**(평가 판단, 로깅, UI 표시)도 같은 작업에서 구현한다 — 계산만 하고 사용하지 않는 필드를 남기지 않는다

## References

| 문서 | 설명 |
|------|------|
| [structure-backend.md](.claude/docs/structure-backend.md) | 백엔드 파일 트리·레이어별 역할·의존 방향 |
| [structure-frontend.md](.claude/docs/structure-frontend.md) | 프론트엔드 파일 트리·컴포넌트·페이지 역할 |
| [architecture-ddd.md](.claude/docs/architecture-ddd.md) | 레이어 다이어그램·REST API 목록·Agent 흐름 |
| [domain-portfolio.md](.claude/docs/domain-portfolio.md) | Portfolio 도메인 명세 |
| [domain-strategy.md](.claude/docs/domain-strategy.md) | TradingStrategy 도메인 명세 |
| [domain-signal-score.md](.claude/docs/domain-signal-score.md) | 신호 점수(signal_score) 계산·게이트·티어 설계, 새 진입 조건 추가 체크리스트 |
| [checklist-development.md](.claude/docs/checklist-development.md) | 구현 완료 후 점검 체크리스트 |
| [kis-api-spec.md](.claude/docs/kis-api-spec.md) | KIS OpenAPI 전체 목록 및 프로젝트 사용 API 상세 스펙 (Request/Response 필드, TR_ID, 예시 포함) |
