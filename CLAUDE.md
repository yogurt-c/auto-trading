# CLAUDE.md

AI-powered financial portfolio management tool — monitors holdings, runs automated trading strategies via Alpaca, and provides a Claude AI agent for natural language interaction.

## Rules

- `frontend/pages/` must only use `frontend.api_client` — never import `backend/` directly
- Alpaca is configured for **Paper Trading** (safe for testing)

## References

| 문서 | 설명 |
|------|------|
| [structure-backend.md](.claude/docs/structure-backend.md) | 백엔드 파일 트리·레이어별 역할·의존 방향 |
| [structure-frontend.md](.claude/docs/structure-frontend.md) | 프론트엔드 파일 트리·컴포넌트·페이지 역할 |
| [architecture-ddd.md](.claude/docs/architecture-ddd.md) | 레이어 다이어그램·REST API 목록·Agent 흐름 |
| [domain-portfolio.md](.claude/docs/domain-portfolio.md) | Portfolio 도메인 명세 |
| [domain-strategy.md](.claude/docs/domain-strategy.md) | TradingStrategy 도메인 명세 |
| [checklist-development.md](.claude/docs/checklist-development.md) | 구현 완료 후 점검 체크리스트 |
