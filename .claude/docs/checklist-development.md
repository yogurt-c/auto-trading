# 구현 체크리스트

구현 완료 후 커밋 전에 아래 항목을 확인한다.

## 문서
- [ ] 구조 변경(레이어 추가·삭제, 파일 이동, API 변경 등) 시 관련 `.claude/docs/*.md` 업데이트

## 테스트 코드
- [ ] 기존 기능 수정 시 해당 테스트 코드도 함께 수정
- [ ] 신규 기능 추가 시 테스트 코드 추가 (`backend/tests/unit/` 또는 `integration/`)

## 테스트 실행
- [ ] `pytest -c backend/pytest.ini` 전체 통과
- [ ] `cd frontend && npm run build` TypeScript 오류 없음

## 프론트엔드 ↔ 백엔드 타입 일치
- [ ] 프론트 페이지 수정 시 백엔드 `response_model` 필드와 `frontend/src/api/types.ts` 인터페이스 일치 확인

## 레이어 의존 방향
- [ ] `backend/domain/` 코드가 `sqlalchemy`, `yfinance` 등 외부 패키지를 import하지 않는가
- [ ] `frontend/src/pages/` 컴포넌트가 `backend/` 경로를 직접 import하지 않고 `frontend/src/api/endpoints.ts`를 통해 접근하는가
