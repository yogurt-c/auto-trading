# 인수인계 (2026-10-20)

## 현재 상태
- P1 Android 앱 1–4단계 완료 (core·kis·engine·app). 전략: 안정형/보수형 월 리밸런싱 (`research/reports/r4_summary.md`)
- 남은 일: **5단계 P5 모의투자** — 실기기에서 최소 2회 월 실행 (11/2, 12/1). 성과가 아닌 안정성 확인

## 새 컴퓨터 준비
1. JDK 21, `brew install --cask android-commandlinetools`
2. `sdkmanager --sdk_root=$(brew --prefix)/share/android-commandlinetools "platform-tools" "platforms;android-35"` (+ `--licenses`)
3. `android/local.properties`: `sdk.dir=<위 경로>` (git 제외)
4. `make android-test` 통과 확인
5. research를 쓸 때만: `research/.env`(키, 직접 옮김)와 `research/data/`(압축본 풀기, 재배포 금지)

## P5에서 실제 응답으로 확인할 것 (명세만 보고 구현함)
- 매수가능조회(VTTC8908R) `nrcvb_buy_amt`에 당일 매도 대금이 포함되는지
- 일자별 시세(FHKST01010400) 응답 형식, 장중 오늘 줄이 있는지 (휴장 판단에 사용)
- 체결조회 `ord_gno_brno`가 취소 주문의 조직번호로 맞는지
- 매도 직후 잔고 `hldg_qty`가 같은 날 줄어드는지
- 시장가 매수가 상한가 기준 금액을 잡는지 (그래서 매수는 현재가 +1% 지정가)

## 그 외
- 2027 KRX 휴장일 발표 시 `android/core/src/main/resources/krx_holidays.json`에 추가 (없어도 시세 유무로 휴장 판단)
- 실전 매매는 잠금 (`AppGraph.ENV = PAPER`). P5 결과를 보고 사용자가 결정한 뒤 잠금 해제 화면을 별도로 설계
