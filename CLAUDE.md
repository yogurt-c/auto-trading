# CLAUDE.md

AI-powered financial portfolio management tool — monitors holdings, runs automated trading strategies via KIS (Korea Investment & Securities), and provides a Claude AI agent for natural language interaction.

## Rules

- `frontend/pages/` must only use `frontend.api_client` — never import `backend/` directly
- KIS is configured for **Paper Trading** (모의투자, safe for testing)
- 구현 완료 후 커밋 전에 반드시 [checklist-development.md](.claude/docs/checklist-development.md)의 모든 항목을 확인하고, 해당 항목을 스스로 실행(테스트 실행·빌드·문서 업데이트 등)한다 — 사용자가 요청하지 않아도 자동으로 수행한다

## References

| 문서 | 설명 |
|------|------|
| [structure-backend.md](.claude/docs/structure-backend.md) | 백엔드 파일 트리·레이어별 역할·의존 방향 |
| [structure-frontend.md](.claude/docs/structure-frontend.md) | 프론트엔드 파일 트리·컴포넌트·페이지 역할 |
| [architecture-ddd.md](.claude/docs/architecture-ddd.md) | 레이어 다이어그램·REST API 목록·Agent 흐름 |
| [domain-portfolio.md](.claude/docs/domain-portfolio.md) | Portfolio 도메인 명세 |
| [domain-strategy.md](.claude/docs/domain-strategy.md) | TradingStrategy 도메인 명세 |
| [checklist-development.md](.claude/docs/checklist-development.md) | 구현 완료 후 점검 체크리스트 |
