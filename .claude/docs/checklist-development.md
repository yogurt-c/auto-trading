# 구현 체크리스트

구현 완료 후 커밋 전에 아래 항목을 확인한다.

## 문서
- [ ] 구조 변경(레이어 추가·삭제, 파일 이동, API 변경 등) 시 관련 `.claude/docs/*.md` 업데이트

## 테스트 코드
- [ ] 기존 기능 수정 시 해당 테스트 코드도 함께 수정
- [ ] 신규 기능 추가 시 테스트 코드 추가 (`backend/tests/unit/` 또는 `integration/`)

## 테스트 실행
- [ ] `make test` 전체 통과
- [ ] `cd frontend && npm run build` TypeScript 오류 없음

## shared/fixtures
- [ ] `backend/app/domain/` 또는 `backend/app/infrastructure/indicators.py`를 바꿨다면 같은 커밋에서 `cd research && .venv/bin/python scripts/gen_fixtures.py` 실행
- [ ] `make research-test` 통과 (research/ 또는 fixtures 변경 시)
- [ ] `research/src/research/rebalance.py`·성향 비중(`config/r3_profiles.yaml`, `r4_conservative.yaml`)을 바꿨다면 fixture 재생성 후 Android `core`도 같이 수정

## Android
- [ ] `cd android && ./gradlew test :app:assembleDebug :app:lintDebug` 통과 (android/ 또는 shared/fixtures 변경 시, Android SDK 필요 — `local.properties`의 `sdk.dir`)
- [ ] `app`: 키·토큰·계좌번호를 로그·알림·화면에 남기지 않는가 (계좌는 `Account.masked`만), 실전 잠금(`AppGraph.ENV`) 유지
- [ ] `engine`: 주문 전송 경로를 바꿨다면 응답 유실·미접수·거부·다음 날 재개 테스트가 여전히 있는지 (`MonthlyRunnerTest`)
- [ ] `kis`: 주문·취소 POST는 네트워크 오류 시 재전송하지 않는다 (OkHttp `retryOnConnectionFailure(false)` 유지). 새 KIS API는 `kis-api-spec.md`에서 모의투자 지원 확인

## DB 마이그레이션
- [ ] `backend/app/infrastructure/models.py` 변경 시 alembic revision 파일 생성했는가

## 코드 품질
- [ ] `make fmt` 실행
- [ ] `make lint` 통과

## 프론트엔드 ↔ 백엔드 타입 일치
- [ ] 프론트 페이지 수정 시 백엔드 `response_model` 필드와 `frontend/src/api/types.ts` 인터페이스 일치 확인

## 레이어 의존 방향
- [ ] `backend/domain/` 코드가 `sqlalchemy`, `yfinance` 등 외부 패키지를 import하지 않는가
- [ ] `frontend/src/pages/` 컴포넌트가 `backend/` 경로를 직접 import하지 않고 `frontend/src/api/endpoints.ts`를 통해 접근하는가

## ORM 필드명 일관성
- [ ] dict key로 ORM 필드에 접근하는 코드가 `models.py` 컬럼명과 정확히 일치하는가 (예: Holding → `shares`, TradeLog → `qty`·`side`)
- [ ] 새 컬럼을 `models.py`에 추가했다면, 해당 컬럼을 사용하는 모든 코드 경로에서 동일한 이름을 사용하는가

## 도메인 필드 완전성
- [ ] 도메인 Value Object에 새 필드를 추가했다면, 그 필드를 **소비하는** 로직(평가 판단, 프롬프트 가이드, UI 표시)도 함께 구현했는가

## 비즈니스 규칙 검증 위치
- [ ] 포지션 한도·시장 시간·주문 유효성 등 비즈니스 불변조건이 **코드 레벨**에서 검증되는가 — LLM 프롬프트 지시에만 의존하는 항목이 없는가
- [ ] I/O가 필요한 비즈니스 규칙 검증(DB 조회 필요)은 Application 레이어에서 처리하는가
