# P1 Android 앱 설계 (2026-10-20 승인)

서버·LLM 없이 폰 혼자 월 1회 리밸런싱을 실행하는 앱. 전략 근거는 `research/reports/r4_summary.md`.

## 1. 하는 일

| 항목 | 내용 |
|------|------|
| 투자 성향 | 안정형 (KODEX 200 50 · TIGER 미국S&P500 50) / 보수형 (25 · 25 · KODEX 국고채3년 50) |
| 실행 시점 | 매월 첫 거래일 09:10 — 전월 마지막 거래일 종가 기준으로 목표 수량 계산 (백테스트와 동일: 월말 판단 → 다음 날 시가 근처 체결) |
| 정기 매수 | 사용자가 계좌에 입금한 현금까지 포함해 `(평가액 + 예수금) x 목표 비중`으로 맞춤 — 입금은 앱 밖에서 (자동이체) |
| 주문 | 매도 먼저 → 체결 확인 → 매수. 매도는 시장가, 매수는 **현재가 +1% 지정가** (KIS 시장가 매수는 상한가 기준으로 주문금액을 잡아 예수금을 다 쓰는 매수가 거부될 수 있음 — 매도호가보다 높은 지정가는 즉시 매도호가에 체결). 주문 1건 금액이 총자산의 1% 미만이면 생략 |
| 성향 변경 | 월 1회. 다음 실행일에 반영 |
| 관리 범위 | 성향 ETF 3종 + 예수금만. 계좌의 다른 종목은 총자산에도 넣지 않고 주문하지 않는다 |
| 알림 | 실행 결과·실패·미체결 |

**하지 않는 것**: 장중 감시, 지표 계산, 종목 선택, 레버리지, 실시간 시세.

## 2. 모듈 (`android/`)

```
core/    순수 Kotlin (Android 의존 없음) — JVM 단위 테스트
  Profile, TargetWeights, Holding, Quote, OrderIntent
  RebalancePlanner   (보유·가격·예수금·목표 비중 → 매도/매수 주문 목록)
                     기준 구현 research/src/research/rebalance.py, fixture shared/fixtures/rebalance
  TradingCalendar    (내장 휴장일 krx_holidays.json + 월 첫 거래일 계산)
kis/     KIS REST 클라이언트 (OkHttp + kotlinx.serialization) — MockWebServer 테스트
engine/  MonthlyRun 유스케이스 — 상태 기계, 재시도, 멱등성
app/     Compose UI, 스케줄링(AlarmManager), Keystore, 알림
```

의존 방향: `app → engine → (core, kis)`, `kis → core`(모델만).

## 3. 사용 KIS API (모의투자 지원 확인: `kis-api-spec.md`)

| 용도 | API | 모의 TR_ID |
|------|-----|-----------|
| 토큰 | 접근토큰발급(P) `/oauth2/tokenP` | — (1분 1회 제한 → 24시간 캐시) |
| 잔고·주문가능수량 | 주식잔고조회 | VTTC8434R |
| 예수금·매수가능 | 매수가능조회 | VTTC8908R |
| 전일 종가 | 주식현재가 일자별 | FHKST01010400 |
| 주문 | 주식주문(현금) | VTTC0011U / VTTC0012U |
| 체결 확인 | 주식일별주문체결조회 | VTTC0081R |
| 미체결 취소 | 주식주문(정정취소) | VTTC0013U |

**재시도 (`kis`)**: 호출 한도(EGW00201)·토큰 만료는 처리되지 않은 요청이라 주문도 다시 보낸다. 연결 끊김·본문 없는 5xx는 조회만 재시도하고, 주문·취소는 `KisException.Transport`로 올려 engine이 주문체결조회로 접수 여부를 확인한다 (OkHttp 자동 재전송도 끔). 토큰 발급의 연결 실패·5xx는 요청을 보내기 전이므로 주문도 다시 시도하고, 키 오류(`Auth`, 재시도 안 함)로 분류하지 않는다. 모의투자는 호출 간격 550ms.

**모의투자 미지원이라 대체하는 것**
- 국내휴장일조회(CTCA0903R) → 앱에 KRX 휴장일 JSON 내장 + 실행 시 확인: 09:10에 `주식현재가 일자별` 최신 일자가 오늘이 아니면 휴장으로 보고 다음 날로 미룸
- 매도가능수량조회 → 잔고조회의 주문가능수량(ord_psbl_qty)

## 4. 월 실행 상태 기계 (engine)

`run_key = YYYY-MM` 당 1회. 상태를 파일(`FileRunStore`)에 저장해 앱이 죽어도 이어서 진행·중복 주문 방지.

```
SCHEDULED → CHECKED_OPEN → PLANNED → SELLS_SENT → SELLS_SETTLED → BUYS_SENT → DONE
                                                                         ↘ FAILED (사유·알림)
```

- PLANNED: 잔고·예수금·전일 종가로 RebalancePlanner 실행, 주문 목록 저장
- SELLS_SENT → SETTLED: 체결조회 폴링 (최대 30분). 미체결은 취소 후 FAILED
- 재시작 시 저장된 주문번호로 체결 여부부터 확인하고 재주문하지 않는다
- 불변조건(코드 레벨): 매수 총액 ≤ 매수가능금액, 매도 수량 ≤ 주문가능수량, 주문 종목은 성향의 ETF 3종만, 하루 주문 건수 ≤ 6, 실전 모드는 별도 확인 스위치 (`MonthlyRunner` 생성 시 검증)

구현 (`engine/MonthlyRunner`):
- `execute(month, profile)`는 몇 번 불러도 안전하다. 결과: `Done` / `Failed`(사유, 알림) / `Postponed(날짜)` (그날 09:10 재실행) / `RetryLater(시각)` (네트워크·호출 한도·토큰 발급 제한·장 시작 전)
- 주문은 보내기 **전에** 기록(주문번호 없음)한다. 응답을 잃으면 다음 실행 때 주문체결조회에서 같은 종목·방향·수량의 짝 없는 주문을 찾아 붙이고, 없으면 접수 안 된 것으로 보고 다시 보낸다
- 매수 계획은 매도 체결 후 한 번만 계산해 저장한다 (다시 계산하면 이미 보낸 매수를 중복할 수 있음)
- 새 주문은 09:05~15:00에만. 거래일이 바뀐 채 재개되면 전날 주문을 확정(당일 주문은 장 마감에 소멸)하고 오늘 잔고로 처음부터 다시 계획한다
- 실패한 달 다시 시도(`retry`): 실패한 날이 오늘이면 주문을 다시 조회해 미체결이 남아 있으면 거부(취소가 안 돼 체결될 수 있음). 아니면 그날 잔고로 처음부터 다시 계획한다. 주문 기록은 남기고 `attempt`로 이전 시도의 주문과 구분한다 (하루 주문 6건 한도는 시도와 무관하게 하루 전체)
- 끝나지 못한 채 달이 바뀐 run은 `isAbandoned` — 기록에 "중단됨"으로 표시
- 저장 형식: `MonthlyRun.toJson()` → `filesDir/runs/run-YYYY-MM.json` (`FileRunStore`: 임시 파일 + fsync + 원자적 이름 변경). Room은 쓰지 않는다 — 달 → JSON 한 덩어리뿐이라 DB가 필요 없다

## 5. 스케줄링

- `AlarmManager.setExactAndAllowWhileIdle` (Android 12+는 `SCHEDULE_EXACT_ALARM` 권한 요청) → 짧은 foreground service로 실행
- 폰이 꺼져 있었거나 알람을 놓친 경우: 부팅·앱 실행 시 이번 달 run이 DONE이 아니고 장중이면 즉시 실행, 장 마감 후면 다음 거래일 09:10
- 배터리 최적화 예외 요청 (안내 화면)

구현 (`engine/RunSchedule` — JVM 테스트, `app`은 연결만):
- 실행은 항상 "그 시각이 속한 달"의 run. 다음 시각: `Done`·`Failed` → 다음 달 첫 거래일 09:10, `Postponed(d)` → d 09:10, `RetryLater(t)` → t
- 깨어날 때(`onWake`: 부팅·앱 업데이트·앱 실행·자동 실행 켜기): 이번 달이 끝났으면 다음 달, 아니면 장중 지금 / 장 전 09:10 / 그 외 다음 거래일 09:10
- 알람(`setExactAndAllowWhileIdle`) → `AlarmReceiver` → `RunService`(foreground, type dataSync) 작업 스레드에서 `MonthlyRunner.execute`. 정확한 알람이어야 백그라운드에서 foreground service를 시작할 수 있다 — 13+는 `USE_EXACT_ALARM`, 12는 `SCHEDULE_EXACT_ALARM`
- 실행 시작 때 15분 뒤 watchdog 알람을 먼저 건다 → 실행 중 프로세스가 죽어도 이어서 진행. 이미 실행 중이면 새 요청은 무시하고 watchdog만 미룬다
- 부팅 때는 알람만 다시 건다 (Android 15는 BOOT_COMPLETED에서 dataSync 시작 금지)
- 실행 결과 → 다음 알람·알림 여부는 `engine/RunCoordinator` (JVM 테스트). 재시도(`RetryLater`)는 알리지 않고, engine이 처리하지 못한 예외는 10분 뒤 재시도 + 오류 알림(소리는 한 번, 예외 종류만 표시)

## 6. 보안

- 앱키·시크릿·계좌번호·토큰: Android Keystore의 AES-GCM 키로 암호화해 저장. 백업 제외 (`allowBackup=false`)
- 로그·알림·화면에 키·토큰 노출 금지, 계좌번호는 마스킹
- 모의/실전 전환: 실전은 기본 잠금, 해제 시 경고 화면

구현 (`app`):
- `SecretBox`: Keystore AES-256-GCM 키(기기 밖 반출 불가)로 파일 1개 암호화, `AtomicFile`. 풀 수 없으면(키 초기화) 다시 입력받는다
- 키·계좌(`kis.bin`)와 토큰(`token.bin`)은 별도 파일. 키를 바꾸면 토큰을 지운다. 키는 잔고 조회로 확인한 뒤에만 저장
- `allowBackup=false` + `dataExtractionRules`로 클라우드 백업·기기 간 이전 모두 제외 (12+는 allowBackup만으로 기기 간 이전을 막지 못함). 평문 HTTP 금지
- 예상하지 못한 예외는 메시지 대신 예외 종류만 화면·알림에 남긴다
- 실전 잠금 해제 화면은 아직 없다 — `AppGraph.ENV = PAPER` 고정, P5 이후에 연다

## 7. 화면

1. 시작: KIS 키·계좌 입력 (모의 기본)
2. 성향 선택: 성향별 비중과 과거 수치 표시 — 최대낙폭(장기 -41% / -19%), 최장 회복 기간, 최악의 해. 기대 수익률은 표시하지 않음
3. 홈: 다음 실행일, 현재 비중 vs 목표 비중, 평가액
4. 기록: 월별 실행 결과·체결 내역
5. 설정: 성향 변경(월 1회), 실행 시각, 모의/실전, 키 재설정

구현: 키 입력 → 성향 선택 → 탭 4개(홈·성향·기록·설정). 홈은 자동 실행 스위치·다음 실행 시각·최근 결과·지금 실행·이번 달 주문/체결. 실행 시각은 09:10 고정. 현재 비중 vs 목표 비중(실시간 평가액)은 아직 없다 — 이번 달 run의 총자산·목표 수량을 보여준다. 이번 달이 실패면 '이번 달 다시 시도' 버튼. 읽을 수 없는 기록 파일은 건너뛰고 기록 화면에 이름만 표시

## 8. 검증

- `shared/fixtures/rebalance/*.json`: research의 Python 리밸런싱 로직(`rotation.py`)으로 생성 → pytest와 Kotlin 테스트가 같은 입력에 같은 주문 수량을 내는지 확인
- kis: MockWebServer로 정상·오류·토큰 만료·rate limit(EGW00201) 응답
- engine: 가짜 KIS로 상태 기계 각 단계 중단·재시작
- P5 모의투자: 최소 2회 월 실행 + 휴장일·앱 강제 종료·네트워크 끊김 시나리오 확인 (성과가 아닌 안정성)

## 9. 작업 순서 (PR 단위)

1. Android 프로젝트 골격 + `core` + 리밸런싱 fixture (Python 생성기 포함) + CI(android.yml, 경로 필터)
2. `kis` 클라이언트
3. `engine` 상태 기계
4. `app` 화면·스케줄링·Keystore
5. 모의투자 실행 (P5)

## 기술 선택

Kotlin 2.1, AGP 8.7, Jetpack Compose (Material3), OkHttp, kotlinx.serialization, coroutines. DI는 수동 생성(`AppGraph`). minSdk 26, targetSdk 35.
