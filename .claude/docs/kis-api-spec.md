# KIS (한국투자증권) OpenAPI 명세서

> Korea Investment & Securities Open Trading API 스펙 문서

> 실전 도메인: `https://openapi.koreainvestment.com:9443`
> 모의 도메인: `https://openapivts.koreainvestment.com:29443`

---

## 목차

1. [공통 헤더](#공통-헤더)
2. [전체 API 목록](#전체-api-목록)
3. [프로젝트 사용 API 상세](#프로젝트-사용-api-상세)

---

## 공통 헤더

모든 REST API 요청에 포함되는 공통 Request Header:

| 헤더명 | 설명 | 필수 |
|--------|------|------|
| `content-type` | `application/json; charset=utf-8` | Y |
| `authorization` | `Bearer {access_token}` (OAuth 접근토큰) | Y |
| `appkey` | 앱키 (KIS 홈페이지 발급) | Y |
| `appsecret` | 앱시크릿키 (KIS 홈페이지 발급) | Y |
| `tr_id` | 거래ID (API별 상이) | Y |
| `custtype` | 고객타입 (`B`: 법인, `P`: 개인) | N |

---

## 전체 API 목록

### OAuth인증

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 1 | REST | Hashkey ⭐ | `Hashkey` | `` | `` | POST | `/uapi/hashkey` |
| 2 | WEBSOCKET | 실시간 (웹소켓) 접속키 발급 | `실시간-000` | `` | `` | POST | `/oauth2/Approval` |
| 3 | REST | 접근토큰폐기(P) | `인증-002` | `` | `` | POST | `/oauth2/revokeP` |
| 4 | REST | 접근토큰발급(P) ⭐ | `인증-001` | `` | `` | POST | `/oauth2/tokenP` |

### [국내주식] 주문/계좌

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 5 | REST | 기간별계좌권리현황조회 | `국내주식-211` | `CTRGA011R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/period-rights` |
| 6 | REST | 투자계좌자산현황조회 | `v1_국내주식-048` | `CTRP6548R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-account-balance` |
| 7 | REST | 퇴직연금 예수금조회 | `v1_국내주식-035` | `TTTC0506R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-deposit` |
| 8 | REST | 주식예약주문정정취소 | `v1_국내주식-018,019` | `(예약취소) CTSC0009U (예약정정) CTSC0013U` | `모의투자 미지원` | POST | `/uapi/domestic-stock/v1/trading/order-resv-rvsecncl` |
| 9 | REST | 신용매수가능조회 | `v1_국내주식-042` | `TTTC8909R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-credit-psamount` |
| 10 | REST | 주식통합증거금 현황 | `국내주식-191` | `TTTC0869R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/intgr-margin` |
| 11 | REST | 퇴직연금 미체결내역 | `v1_국내주식-033` | `TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR)` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld` |
| 12 | REST | 기간별매매손익현황조회 | `v1_국내주식-060` | `TTTC8715R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` |
| 13 | REST | 주식주문(정정취소) ⭐ | `v1_국내주식-003` | `TTTC0013U` | `VTTC0013U` | POST | `/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 14 | REST | 주식예약주문조회 | `v1_국내주식-020` | `CTSC0004R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/order-resv-ccnl` |
| 15 | REST | 퇴직연금 매수가능조회 | `v1_국내주식-034` | `TTTC0503R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order` |
| 16 | REST | 주식잔고조회 ⭐ | `v1_국내주식-006` | `TTTC8434R` | `VTTC8434R` | GET | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| 17 | REST | 퇴직연금 체결기준잔고 | `v1_국내주식-032` | `TTTC2202R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-present-balance` |
| 18 | REST | 매수가능조회 | `v1_국내주식-007` | `TTTC8908R` | `VTTC8908R` | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` |
| 19 | REST | 기간별손익일별합산조회 | `v1_국내주식-052` | `TTTC8708R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-period-profit` |
| 20 | REST | 주식주문(현금) ⭐ | `v1_국내주식-001` | `(매도) TTTC0011U (매수) TTTC0012U` | `(매도) VTTC0011U (매수) VTTC0012U` | POST | `/uapi/domestic-stock/v1/trading/order-cash` |
| 21 | REST | 매도가능수량조회 | `국내주식-165` | `TTTC8408R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-sell` |
| 22 | REST | 주식일별주문체결조회 ⭐ | `v1_국내주식-005` | `(3개월이내) TTTC0081R (3개월이전) CTSC9215R` | `(3개월이내) VTTC0081R (3개월이전) VTSC9215R` | GET | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| 23 | REST | 주식정정취소가능주문조회 | `v1_국내주식-004` | `TTTC0084R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` |
| 24 | REST | 주식예약주문 | `v1_국내주식-017` | `CTSC0008U` | `모의투자 미지원` | POST | `/uapi/domestic-stock/v1/trading/order-resv` |
| 25 | REST | 주식주문(신용) | `v1_국내주식-002` | `(매도) TTTC0051U (매수) TTTC0052U` | `모의투자 미지원` | POST | `/uapi/domestic-stock/v1/trading/order-credit` |
| 26 | REST | 퇴직연금 잔고조회 | `v1_국내주식-036` | `TTTC2208R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/pension/inquire-balance` |
| 27 | REST | 주식잔고조회_실현손익 | `v1_국내주식-041` | `TTTC8494R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl` |

### [국내주식] 기본시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 28 | REST | 주식현재가 일자별 | `v1_국내주식-010` | `FHKST01010400` | `FHKST01010400` | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-price` |
| 29 | REST | 주식현재가 시세 ⭐ | `v1_국내주식-008` | `FHKST01010100` | `FHKST01010100` | GET | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| 30 | REST | 국내주식 시간외현재가 | `국내주식-076` | `FHPST02300000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-price` |
| 31 | REST | ETF 구성종목시세 | `국내주식-073` | `FHKST121600C0` | `모의투자 미지원` | GET | `/uapi/etfetn/v1/quotations/inquire-component-stock-price` |
| 32 | REST | 주식현재가 시간외시간별체결 | `v1_국내주식-025` | `FHPST02310000` | `FHPST02310000` | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion` |
| 33 | REST | NAV 비교추이(종목) | `v1_국내주식-069` | `FHPST02440000` | `모의투자 미지원` | GET | `/uapi/etfetn/v1/quotations/nav-comparison-trend` |
| 34 | REST | 주식현재가 시간외일자별주가 | `v1_국내주식-026` | `FHPST02320000` | `FHPST02320000` | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice` |
| 35 | REST | 국내주식 시간외호가 | `국내주식-077` | `FHPST02300400` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price` |
| 36 | REST | 주식현재가 당일시간대별체결 | `v1_국내주식-023` | `FHPST01060000` | `FHPST01060000` | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` |
| 37 | REST | 주식현재가 시세2 | `v1_국내주식-054` | `FHPST01010000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-price-2` |
| 38 | REST | 주식일별분봉조회 | `국내주식-213` | `FHKST03010230` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice` |
| 39 | REST | 국내주식기간별시세(일/주/월/년) | `v1_국내주식-016` | `FHKST03010100` | `FHKST03010100` | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` |
| 40 | REST | NAV 비교추이(일) | `v1_국내주식-071` | `FHPST02440200` | `모의투자 미지원` | GET | `/uapi/etfetn/v1/quotations/nav-comparison-daily-trend` |
| 41 | REST | 주식현재가 호가/예상체결 | `v1_국내주식-011` | `FHKST01010200` | `FHKST01010200` | GET | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` |
| 42 | REST | 주식현재가 체결 | `v1_국내주식-009` | `FHKST01010300` | `FHKST01010300` | GET | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` |
| 43 | REST | 주식현재가 회원사 | `v1_국내주식-013` | `FHKST01010600` | `FHKST01010600` | GET | `/uapi/domestic-stock/v1/quotations/inquire-member` |
| 44 | REST | NAV 비교추이(분) | `v1_국내주식-070` | `FHPST02440100` | `모의투자 미지원` | GET | `/uapi/etfetn/v1/quotations/nav-comparison-time-trend` |
| 45 | REST | 주식현재가 투자자 | `v1_국내주식-012` | `FHKST01010900` | `FHKST01010900` | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor` |
| 46 | REST | ETF/ETN 현재가 | `v1_국내주식-068` | `FHPST02400000` | `모의투자 미지원` | GET | `/uapi/etfetn/v1/quotations/inquire-price` |
| 47 | REST | 국내주식 장마감 예상체결가 | `국내주식-120` | `FHKST117300C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/exp-closing-price` |
| 48 | REST | 주식당일분봉조회 | `v1_국내주식-022` | `FHKST03010200` | `FHKST03010200` | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` |

### [국내주식] ELW 시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 49 | REST | ELW 현재가 시세 | `v1_국내주식-014` | `FHKEW15010000` | `FHKEW15010000` | GET | `/uapi/domestic-stock/v1/quotations/inquire-elw-price` |
| 50 | REST | ELW 신규상장종목 | `국내주식-181` | `FHKEW154800C0` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/newly-listed` |
| 51 | REST | ELW 투자지표추이(일별) | `국내주식-173` | `FHPEW02740200` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/indicator-trend-daily` |
| 52 | REST | ELW 민감도 순위 | `국내주식-170` | `FHPEW02850000` | `모의투자 미지원` | GET | `/uapi/elw/v1/ranking/sensitivity` |
| 53 | REST | ELW 기초자산별 종목시세 | `국내주식-186` | `FHKEW154101C0` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/udrl-asset-price` |
| 54 | REST | ELW 종목검색 | `국내주식-166` | `FHKEW15100000` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/cond-search` |
| 55 | REST | ELW 변동성 추이(분별) | `국내주식-179` | `FHPEW02840300` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/volatility-trend-minute` |
| 56 | REST | ELW 변동성추이(체결) | `국내주식-177` | `FHPEW02840100` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/volatility-trend-ccnl` |
| 57 | REST | ELW 당일급변종목 | `국내주식-171` | `FHPEW02870000` | `모의투자 미지원` | GET | `/uapi/elw/v1/ranking/quick-change` |
| 58 | REST | ELW 투자지표추이(분별) | `국내주식-174` | `FHPEW02740300` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/indicator-trend-minute` |
| 59 | REST | ELW 기초자산 목록조회 | `국내주식-185` | `FHKEW154100C0` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/udrl-asset-list` |
| 60 | REST | ELW 변동성 추이(일별) | `국내주식-178` | `FHPEW02840200` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/volatility-trend-daily` |
| 61 | REST | ELW 거래량순위 | `국내주식-168` | `FHPEW02780000` | `모의투자 미지원` | GET | `/uapi/elw/v1/ranking/volume-rank` |
| 62 | REST | ELW 지표순위 | `국내주식-169` | `FHPEW02790000` | `모의투자 미지원` | GET | `/uapi/elw/v1/ranking/indicator` |
| 63 | REST | ELW 투자지표추이(체결) | `국내주식-172` | `FHPEW02740100` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/indicator-trend-ccnl` |
| 64 | REST | ELW 상승률순위 | `국내주식-167` | `FHPEW02770000` | `모의투자 미지원` | GET | `/uapi/elw/v1/ranking/updown-rate` |
| 65 | REST | ELW 민감도 추이(일별) | `국내주식-176` | `FHPEW02830200` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/sensitivity-trend-daily` |
| 66 | REST | ELW 비교대상종목조회 | `국내주식-183` | `FHKEW151701C0` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/compare-stocks` |
| 67 | REST | ELW 만기예정/만기종목 | `국내주식-184` | `FHKEW154700C0` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/expiration-stocks` |
| 68 | REST | ELW LP매매추이 | `국내주식-182` | `FHPEW03760000` | `` | GET | `/uapi/elw/v1/quotations/lp-trade-trend` |
| 69 | REST | ELW 민감도 추이(체결) | `국내주식-175` | `FHPEW02830100` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/sensitivity-trend-ccnl` |
| 70 | REST | ELW 변동성 추이(틱) | `국내주식-180` | `FHPEW02840400` | `모의투자 미지원` | GET | `/uapi/elw/v1/quotations/volatility-trend-tick` |

### [국내주식] 업종/기타

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 71 | REST | 국내주식 예상체결지수 추이 | `국내주식-121` | `FHPST01840000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/exp-index-trend` |
| 72 | REST | 국내주식업종기간별시세(일/주/월/년) | `v1_국내주식-021` | `FHKUP03500100` | `FHKUP03500100` | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice` |
| 73 | REST | 국내업종 시간별지수(분) | `국내주식-119` | `FHPUP02110200` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-timeprice` |
| 74 | REST | 국내업종 구분별전체시세 | `v1_국내주식-066` | `FHPUP02140000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-category-price` |
| 75 | REST | 업종 분봉조회 | `v1_국내주식-045` | `FHKUP03500200` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice` |
| 76 | REST | 국내휴장일조회 | `국내주식-040` | `CTCA0903R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/chk-holiday` |
| 77 | REST | 국내주식 예상체결 전체지수 | `국내주식-122` | `FHKUP11750000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/exp-total-index` |
| 78 | REST | 국내업종 현재지수 | `v1_국내주식-063` | `FHPUP02100000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-price` |
| 79 | REST | 국내선물 영업일조회 | `국내주식-160` | `HHMCM000002C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/market-time` |
| 80 | REST | 국내업종 시간별지수(초) | `국내주식-064` | `FHPUP02110100` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-tickprice` |
| 81 | REST | 국내업종 일자별지수 | `v1_국내주식-065` | `FHPUP02120000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-index-daily-price` |
| 82 | REST | 금리 종합(국내채권/금리) | `국내주식-155` | `FHPST07020000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/comp-interest` |
| 83 | REST | 변동성완화장치(VI) 현황 | `v1_국내주식-055` | `FHPST01390000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-vi-status` |
| 84 | REST | 종합 시황/공시(제목) | `국내주식-141` | `FHKST01011800` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/news-title` |

### [국내주식] 종목정보

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 85 | REST | 상품기본조회 | `v1_국내주식-029` | `CTPF1604R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/search-info` |
| 86 | REST | 예탁원정보(상장정보일정) | `국내주식-150` | `HHKDB669107C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/list-info` |
| 87 | REST | 예탁원정보(공모주청약일정) | `국내주식-151` | `HHKDB669108C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/pub-offer` |
| 88 | REST | 국내주식 재무비율 | `v1_국내주식-080` | `FHKST66430300` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/financial-ratio` |
| 89 | REST | 예탁원정보(자본감소일정) | `국내주식-149` | `HHKDB669106C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/cap-dcrs` |
| 90 | REST | 예탁원정보(무상증자일정) | `국내주식-144` | `HHKDB669101C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/bonus-issue` |
| 91 | REST | 국내주식 증권사별 투자의견 | `국내주식-189` | `FHKST663400C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/invest-opbysec` |
| 92 | REST | 국내주식 당사 신용가능종목 | `국내주식-111` | `FHPST04770000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/credit-by-company` |
| 93 | REST | 예탁원정보(주식매수청구일정) | `국내주식-146` | `HHKDB669103C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/purreq` |
| 94 | REST | 예탁원정보(액면교체일정) | `국내주식-148` | `HHKDB669105C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/rev-split` |
| 95 | REST | 예탁원정보(배당일정) | `국내주식-145` | `HHKDB669102C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/dividend` |
| 96 | REST | 국내주식 종목투자의견 | `국내주식-188` | `FHKST663300C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/invest-opinion` |
| 97 | REST | 국내주식 안정성비율 | `v1_국내주식-083` | `FHKST66430600` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/stability-ratio` |
| 98 | REST | 국내주식 수익성비율 | `v1_국내주식-081` | `FHKST66430400` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/profit-ratio` |
| 99 | REST | 예탁원정보(실권주일정) | `국내주식-152` | `HHKDB669109C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/forfeit` |
| 100 | REST | 예탁원정보(의무예치일정) | `국내주식-153` | `HHKDB669110C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/mand-deposit` |
| 101 | REST | 국내주식 손익계산서 | `v1_국내주식-079` | `FHKST66430200` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/income-statement` |
| 102 | REST | 당사 대주가능 종목 | `국내주식-195` | `CTSC2702R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/lendable-by-company` |
| 103 | REST | 주식기본조회 | `v1_국내주식-067` | `CTPF1002R` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/search-stock-info` |
| 104 | REST | 예탁원정보(유상증자일정) | `국내주식-143` | `HHKDB669100C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/paidin-capin` |
| 105 | REST | 예탁원정보(주주총회일정) | `국내주식-154` | `HHKDB669111C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/sharehld-meet` |
| 106 | REST | 국내주식 성장성비율 | `v1_국내주식-085` | `FHKST66430800` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/growth-ratio` |
| 107 | REST | 국내주식 대차대조표 | `v1_국내주식-078` | `FHKST66430100` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/balance-sheet` |
| 108 | REST | 예탁원정보(합병/분할일정) | `국내주식-147` | `HHKDB669104C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ksdinfo/merger-split` |
| 109 | REST | 국내주식 종목추정실적 | `국내주식-187` | `HHKST668300C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/estimate-perform` |
| 110 | REST | 국내주식 기타주요비율 | `v1_국내주식-082` | `FHKST66430500` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/finance/other-major-ratios` |

### [국내주식] 시세분석

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 111 | REST | 프로그램매매 종합현황(시간) | `국내주식-114` | `FHPPG04600101` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-today` |
| 112 | REST | 국내주식 신용잔고 일별추이 | `국내주식-110` | `FHPST04760000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/daily-credit-balance` |
| 113 | REST | 시장별 투자자매매동향(일별) | `국내주식-075` | `FHPTJ04040000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market` |
| 114 | REST | 국내주식 공매도 일별추이 | `국내주식-134` | `FHPST04830000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/daily-short-sale` |
| 115 | REST | 종목별 투자자매매동향(일별) | `종목별 투자자매매동향(일별)` | `FHPTJ04160001` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily` |
| 116 | REST | 종목조건검색 목록조회 | `국내주식-038` | `HHKST03900300` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/psearch-title` |
| 117 | REST | 국내주식 상하한가 포착 | `국내주식-190` | `FHKST130000C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/capture-uplowprice` |
| 118 | REST | 프로그램매매 종합현황(일별) | `국내주식-115` | `FHPPG04600001` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/comp-program-trade-daily` |
| 119 | REST | 종목별 일별 대차거래추이 | `국내주식-135` | `HHPST074500C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/daily-loan-trans` |
| 120 | REST | 종목조건검색조회 | `국내주식-039` | `HHKST03900400` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/psearch-result` |
| 121 | REST | 국내주식 매물대/거래비중 | `국내주식-196` | `FHPST01130000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/pbar-tratio` |
| 122 | REST | 국내기관_외국인 매매종목가집계 | `국내주식-037` | `FHPTJ04400000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/foreign-institution-total` |
| 123 | REST | 관심종목 그룹별 종목조회 | `국내주식-203` | `HHKCM113004C6` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group` |
| 124 | REST | 주식현재가 회원사 종목매매동향 | `국내주식-197` | `FHPST04540000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-member-daily` |
| 125 | REST | 종목별 프로그램매매추이(일별) | `국내주식-113` | `FHPPG04650201` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily` |
| 126 | REST | 관심종목 그룹조회 | `국내주식-204` | `HHKCM113004C7` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/intstock-grouplist` |
| 127 | REST | 종목별 외인기관 추정가집계 | `v1_국내주식-046` | `HHPTJ04160200` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/investor-trend-estimate` |
| 128 | REST | 종목별일별매수매도체결량 | `v1_국내주식-056` | `FHKST03010800` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume` |
| 129 | REST | 국내주식 체결금액별 매매비중 | `국내주식-192` | `FHKST111900C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/tradprt-byamt` |
| 130 | REST | 프로그램매매 투자자매매동향(당일) | `국내주식-116` | `HHPPG046600C1` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/investor-program-trade-today` |
| 131 | REST | 국내 증시자금 종합 | `국내주식-193` | `FHKST649100C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/mktfunds` |
| 132 | REST | 국내주식 예상체결가 추이 | `국내주식-118` | `FHPST01810000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/exp-price-trend` |
| 133 | WEBSOCKET | 회원사 실시간 매매동향(틱) | `국내주식-163` | `FHPST04320000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-trend` |
| 134 | REST | 시장별 투자자매매동향(시세) | `v1_국내주식-074` | `FHPTJ04030000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market` |
| 135 | REST | 종목별 프로그램매매추이(체결) | `v1_국내주식-044` | `FHPPG04650101` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock` |
| 136 | REST | 외국계 매매종목 가집계 | `국내주식-161` | `FHKST644100C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate` |
| 137 | REST | 국내주식 시간외예상체결등락률 | `국내주식-140` | `FHKST11860000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct` |
| 138 | REST | 종목별 외국계 순매수추이 | `국내주식-164` | `FHKST644400C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend` |
| 139 | REST | 관심종목(멀티종목) 시세조회 | `국내주식-205` | `FHKST11300006` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/intstock-multprice` |

### [국내주식] 순위분석

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 140 | REST | 국내주식 예상체결 상승/하락상위 | `v1_국내주식-103` | `FHPST01820000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/exp-trans-updown` |
| 141 | REST | 국내주식 호가잔량 순위 | `국내주식-089` | `FHPST01720000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/quote-balance` |
| 142 | REST | 국내주식 신용잔고 상위 | `국내주식-109` | `FHKST17010000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/credit-balance` |
| 143 | REST | 국내주식 시간외거래량순위 | `국내주식-139` | `FHPST02350000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/overtime-volume` |
| 144 | REST | 국내주식 배당률 상위 | `국내주식-106` | `HHKDB13470100` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/dividend-rate` |
| 145 | REST | 국내주식 시간외잔량 순위 | `v1_국내주식-093` | `FHPST01760000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/after-hour-balance` |
| 146 | REST | 국내주식 공매도 상위종목 | `국내주식-133` | `FHPST04820000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/short-sale` |
| 147 | REST | 국내주식 이격도 순위 | `v1_국내주식-095` | `FHPST01780000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/disparity` |
| 148 | REST | HTS조회상위20종목 | `국내주식-214` | `HHMCM000100C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/hts-top-view` |
| 149 | REST | 거래량순위 | `v1_국내주식-047` | `FHPST01710000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/quotations/volume-rank` |
| 150 | REST | 국내주식 수익자산지표 순위 | `v1_국내주식-090` | `FHPST01730000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/profit-asset-index` |
| 151 | REST | 국내주식 신고/신저근접종목 상위 | `v1_국내주식-105` | `FHPST01870000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/near-new-highlow` |
| 152 | REST | 국내주식 우선주/괴리율 상위 | `v1_국내주식-094` | `FHPST01770000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/prefer-disparate-ratio` |
| 153 | REST | 국내주식 대량체결건수 상위 | `국내주식-107` | `FHKST190900C0` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/bulk-trans-num` |
| 154 | REST | 국내주식 재무비율 순위 | `v1_국내주식-092` | `FHPST01750000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/finance-ratio` |
| 155 | REST | 국내주식 시가총액 상위 | `v1_국내주식-091` | `FHPST01740000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/market-cap` |
| 156 | REST | 국내주식 당사매매종목 상위 | `v1_국내주식-104` | `FHPST01860000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/traded-by-company` |
| 157 | REST | 국내주식 등락률 순위 | `v1_국내주식-088` | `FHPST01700000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/fluctuation` |
| 158 | REST | 국내주식 시장가치 순위 | `v1_국내주식-096` | `FHPST01790000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/market-value` |
| 159 | REST | 국내주식 관심종목등록 상위 | `v1_국내주식-102` | `FHPST01800000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/top-interest-stock` |
| 160 | REST | 국내주식 체결강도 상위 | `v1_국내주식-101` | `FHPST01680000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/volume-power` |
| 161 | REST | 국내주식 시간외등락율순위 | `국내주식-138` | `FHPST02340000` | `모의투자 미지원` | GET | `/uapi/domestic-stock/v1/ranking/overtime-fluctuation` |

### [국내주식] 실시간시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 162 | WEBSOCKET | 국내지수 실시간예상체결 | `실시간-027` | `H0UPANC0` | `모의투자 미지원` | POST | `/tryitout/H0UPANC0` |
| 163 | REST | 국내주식 장운영정보 (통합) | `국내주식 장운영정보 (통합)` | `H0UNMKO0` | `모의투자 미지원` | POST | `/tryitout/H0UNMKO0` |
| 164 | WEBSOCKET | 국내주식 실시간회원사 (NXT) | `국내주식 실시간회원사 (NXT)` | `H0NXMBC0` | `모의투자 미지원` | POST | `/tryitout/H0NXMBC0` |
| 165 | WEBSOCKET | 국내주식 실시간체결통보 | `실시간-005` | `H0STCNI0` | `H0STCNI9` | POST | `/tryitout/H0STCNI0` |
| 166 | WEBSOCKET | 국내주식 시간외 실시간예상체결 (KRX) | `실시간-024` | `H0STOAC0` | `모의투자 미지원` | POST | `/tryitout/H0STOAC0` |
| 167 | WEBSOCKET | 국내주식 시간외 실시간호가 (KRX) | `실시간-025` | `H0STOAA0` | `모의투자 미지원` | POST | `/tryitout/H0STOAA0` |
| 168 | WEBSOCKET | 국내주식 실시간프로그램매매 (통합) | `국내주식 실시간프로그램매매 (통합)` | `H0UNPGM0` | `모의투자 미지원` | POST | `/tryitout/H0UNPGM0` |
| 169 | WEBSOCKET | 국내주식 실시간호가 (통합) | `국내주식 실시간호가 (통합)` | `H0UNASP0` | `모의투자 미지원` | POST | `/tryitout/H0UNASP0` |
| 170 | WEBSOCKET | 국내주식 실시간프로그램매매 (KRX) | `실시간-048` | `H0STPGM0` | `모의투자 미지원` | POST | `/tryitout/H0STPGM0` |
| 171 | WEBSOCKET | 국내주식 장운영정보 (KRX) | `실시간-049` | `H0STMKO0` | `모의투자 미지원` | POST | `/tryitout/H0STMKO0` |
| 172 | WEBSOCKET | 국내주식 실시간체결가 (KRX) | `실시간-003` | `H0STCNT0` | `H0STCNT0` | POST | `/tryitout/H0STCNT0` |
| 173 | WEBSOCKET | 국내지수 실시간프로그램매매 | `실시간-028` | `H0UPPGM0` | `모의투자 미지원` | POST | `/tryitout/H0UPPGM0` |
| 174 | WEBSOCKET | 국내주식 실시간회원사 (통합) | `국내주식 실시간회원사 (통합)` | `H0UNMBC0` | `모의투자 미지원` | POST | `/tryitout/H0UNMBC0` |
| 175 | WEBSOCKET | 국내지수 실시간체결 | `실시간-026` | `H0UPCNT0` | `모의투자 미지원` | POST | `/tryitout/H0UPCNT0` |
| 176 | WEBSOCKET | 국내주식 실시간예상체결 (KRX) | `실시간-041` | `H0STANC0` | `모의투자 미지원` | POST | `/tryitout/H0STANC0` |
| 177 | WEBSOCKET | ELW 실시간호가 | `실시간-062` | `H0EWASP0` | `모의투자 미지원` | POST | `/tryitout/H0EWASP0` |
| 178 | WEBSOCKET | 국내주식 실시간호가 (KRX) | `실시간-004` | `H0STASP0` | `H0STASP0` | POST | `/tryitout/H0STASP0` |
| 179 | WEBSOCKET | 국내주식 실시간체결가 (통합) | `국내주식 실시간체결가 (통합)` | `H0UNCNT0` | `모의투자 미지원` | POST | `/tryitout/H0UNCNT0` |
| 180 | WEBSOCKET | 국내주식 실시간호가 (NXT) | `국내주식 실시간호가 (NXT)` | `H0NXASP0` | `모의투자 미지원` | POST | `/tryitout/H0NXASP0` |
| 181 | WEBSOCKET | 국내주식 실시간프로그램매매 (NXT) | `국내주식 실시간프로그램매매 (NXT)` | `H0NXPGM0` | `모의투자 미지원` | POST | `/tryitout/H0NXPGM0` |
| 182 | WEBSOCKET | 국내주식 실시간체결가 (NXT) | `국내주식 실시간체결가 (NXT)` | `H0NXCNT0` | `모의투자 미지원` | POST | `/tryitout/H0NXCNT0` |
| 183 | WEBSOCKET | ELW 실시간체결가 | `실시간-061` | `H0EWCNT0` | `모의투자 미지원` | POST | `/tryitout/H0EWCNT0` |
| 184 | WEBSOCKET | ELW 실시간예상체결 | `실시간-063` | `H0EWANC0` | `모의투자 미지원` | POST | `/tryitout/H0EWANC0` |
| 185 | WEBSOCKET | 국내주식 실시간예상체결 (NXT) | `국내주식 실시간예상체결 (NXT)` | `H0NXANC0` | `모의투자 미지원` | POST | `/tryitout/H0NXANC0` |
| 186 | WEBSOCKET | 국내주식 실시간회원사 (KRX) | `실시간-047` | `H0STMBC0` | `모의투자 미지원` | POST | `/tryitout/H0STMBC0` |
| 187 | WEBSOCKET | 국내주식 실시간예상체결 (통합) | `국내주식 실시간예상체결 (통합)` | `H0UNANC0` | `모의투자 미지원` | POST | `/tryitout/H0UNANC0` |
| 188 | REST | 국내주식 장운영정보 (NXT) | `국내주식 장운영정보 (NXT)` | `H0NXMKO0` | `모의투자 미지원` | POST | `/tryitout/H0NXMKO0` |
| 189 | WEBSOCKET | 국내ETF NAV추이 | `실시간-051` | `H0STNAV0` | `모의투자 미지원` | POST | `/tryitout/H0STNAV0` |
| 190 | WEBSOCKET | 국내주식 시간외 실시간체결가 (KRX) | `실시간-042` | `H0STOUP0` | `모의투자 미지원` | POST | `/tryitout/H0STOUP0` |

### [국내선물옵션] 주문/계좌

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 191 | REST | (야간)선물옵션 증거금 상세 | `국내선물-024` | `(구) JTCE6003R (신) CTFN7107R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/ngt-margin-detail` |
| 192 | REST | 선물옵션 총자산현황 | `v1_국내선물-014` | `CTRP6550R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-deposit` |
| 193 | REST | 선물옵션기간약정수수료일별 | `v1_국내선물-017` | `CTFO6119R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-daily-amount-fee` |
| 194 | REST | (야간)선물옵션 잔고현황 | `국내선물-010` | `(구) JTCE6001R (신) CTFN6118R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-balance` |
| 195 | REST | 선물옵션 잔고현황 | `v1_국내선물-004` | `CTFO6118R` | `VTFO6118R` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance` |
| 196 | REST | 선물옵션 주문 | `v1_국내선물-001` | `(주간 매수/매도) TTTO1101U (야간 매수/매도) (구) JTCE1001U (신) STTN1101U` | `(주간 매수/매도) VTTO1101U (야간은 모의투자 미제공)` | POST | `/uapi/domestic-futureoption/v1/trading/order` |
| 197 | REST | 선물옵션 잔고평가손익내역 | `v1_국내선물-015` | `CTFO6159R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-valuation-pl` |
| 198 | REST | 선물옵션 증거금률 | `선물옵션 증거금률` | `TTTO6032R` | `미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/margin-rate` |
| 199 | REST | 선물옵션 정정취소주문 | `v1_국내선물-002` | `(주간 정정/취소) TTTO1103U (야간 정정/취소) (구) JTCE1002U (신) STTN1103U` | `(주간 정정/취소) VTTO1103U (야간은 모의투자 미제공)` | POST | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` |
| 200 | REST | 선물옵션 주문체결내역조회 | `v1_국내선물-003` | `TTTO5201R` | `VTTO5201R` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl` |
| 201 | REST | (야간)선물옵션 주문체결 내역조회 | `국내선물-009` | `(구) JTCE5005R (신) STTN5201R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-ccnl` |
| 202 | REST | (야간)선물옵션 주문가능 조회 | `국내선물-011` | `(구) JTCE1004R (신) STTN5105R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-ngt-order` |
| 203 | REST | 선물옵션 잔고정산손익내역 | `v1_국내선물-013` | `CTFO6117R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-balance-settlement-pl` |
| 204 | REST | 선물옵션 주문가능 | `v1_국내선물-005` | `TTTO5105R` | `VTTO5105R` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-order` |
| 205 | REST | 선물옵션 기준일체결내역 | `v1_국내선물-016` | `CTFO5139R` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl-bstime` |

### [국내선물옵션] 기본시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 206 | REST | 선물옵션 시세 | `v1_국내선물-006` | `FHMIF10000000` | `FHMIF10000000` | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-price` |
| 207 | REST | 국내선물 기초자산 시세 | `국내선물-021` | `FHPIF05030000` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-top` |
| 208 | REST | 선물옵션 일중예상체결추이 | `국내선물-018` | `FHPIF05110100` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/exp-price-trend` |
| 209 | REST | 선물옵션기간별시세(일/주/월/년) | `v1_국내선물-008` | `FHKIF03020100` | `FHKIF03020100` | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice` |
| 210 | REST | 국내옵션전광판_선물 | `국내선물-023` | `FHPIF05030200` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-futures` |
| 211 | REST | 선물옵션 분봉조회 | `v1_국내선물-012` | `FHKIF03020200` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice` |
| 212 | REST | 국내옵션전광판_옵션월물리스트 | `국내선물-020` | `FHPIO056104C0` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-option-list` |
| 213 | REST | 선물옵션 시세호가 | `v1_국내선물-007` | `FHMIF10010000` | `FHMIF10010000` | GET | `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` |
| 214 | REST | 국내옵션전광판_콜풋 | `국내선물-022` | `FHPIF05030100` | `모의투자 미지원` | GET | `/uapi/domestic-futureoption/v1/quotations/display-board-callput` |

### [국내선물옵션] 실시간시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 215 | WEBSOCKET | 주식옵션 실시간호가 | `실시간-045` | `H0ZOASP0` | `모의투자 미지원` | POST | `/tryitout/H0ZOASP0` |
| 216 | WEBSOCKET | 선물옵션 실시간체결통보 | `실시간-012` | `H0IFCNI0` | `H0IFCNI9` | POST | `/tryitout/H0IFCNI0` |
| 217 | WEBSOCKET | KRX야간선물 실시간종목체결 | `실시간-064` | `H0MFCNT0` | `모의투자 미지원` | POST | `/tryitout/H0MFCNT0` |
| 218 | WEBSOCKET | KRX야간선물 실시간호가 | `실시간-065` | `H0MFASP0` | `모의투자 미지원` | POST | `/tryitout/H0MFASP0` |
| 219 | WEBSOCKET | KRX야간옵션 실시간체결가 | `실시간-032` | `H0EUCNT0` | `모의투자 미지원` | POST | `/tryitout/H0EUCNT0` |
| 220 | WEBSOCKET | KRX야간옵션실시간예상체결 | `실시간-034` | `H0EUANC0` | `모의투자 미지원` | POST | `/tryitout/H0EUANC0` |
| 221 | WEBSOCKET | 지수선물 실시간체결가 | `실시간-010` | `H0IFCNT0` | `모의투자 미지원` | POST | `/tryitout/H0IFCNT0` |
| 222 | WEBSOCKET | 주식선물 실시간예상체결 | `실시간-031` | `H0ZFANC0` | `모의투자 미지원` | POST | `/tryitout/H0ZFANC0` |
| 223 | WEBSOCKET | KRX야간옵션실시간체결통보 | `실시간-067` | `H0MFCNI0` | `모의투자 미지원` | POST | `/tryitout/H0EUCNI0` |
| 224 | WEBSOCKET | KRX야간선물 실시간체결통보 | `실시간-066` | `H0MFCNI0` | `모의투자 미지원` | POST | `/tryitout/H0MFCNI0` |
| 225 | WEBSOCKET | 상품선물 실시간체결가 | `실시간-022` | `H0CFCNT0` | `모의투자 미지원` | POST | `/tryitout/H0CFCNT0` |
| 226 | WEBSOCKET | 지수선물 실시간호가 | `실시간-011` | `H0IFASP0` | `모의투자 미지원` | POST | `/tryitout/H0IFASP0` |
| 227 | WEBSOCKET | 지수옵션  실시간체결가 | `실시간-014` | `H0IOCNT0` | `모의투자 미지원` | POST | `/tryitout/H0IOCNT0` |
| 228 | WEBSOCKET | KRX야간옵션 실시간호가 | `실시간-033` | `H0EUASP0` | `모의투자 미지원` | POST | `/tryitout/H0EUASP0` |
| 229 | WEBSOCKET | 상품선물 실시간호가 | `실시간-023` | `H0CFASP0` | `모의투자 미지원` | POST | `/tryitout/H0CFASP0` |
| 230 | WEBSOCKET | 주식옵션 실시간예상체결 | `실시간-046` | `H0ZOANC0` | `모의투자 미지원` | POST | `/tryitout/H0ZOANC0` |
| 231 | WEBSOCKET | 주식선물 실시간호가 | `실시간-030` | `H0ZFASP0` | `모의투자 미지원` | POST | `/tryitout/H0ZFASP0` |
| 232 | WEBSOCKET | 주식옵션 실시간체결가 | `실시간-044` | `H0ZOCNT0` | `모의투자 미지원` | POST | `/tryitout/H0ZOCNT0` |
| 233 | WEBSOCKET | 지수옵션 실시간호가 | `실시간-015` | `H0IOASP0` | `모의투자 미지원` | POST | `/tryitout/H0IOASP0` |
| 234 | WEBSOCKET | 주식선물 실시간체결가 | `실시간-029` | `H0ZFCNT0` | `모의투자 미지원` | POST | `/tryitout/H0ZFCNT0` |

### [해외주식] 주문/계좌

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 235 | REST | 해외주식 잔고 | `v1_해외주식-006` | `TTTS3012R` | `VTTS3012R` | GET | `/uapi/overseas-stock/v1/trading/inquire-balance` |
| 236 | REST | 해외주식 체결기준현재잔고 | `v1_해외주식-008` | `CTRP6504R` | `VTRP6504R` | GET | `/uapi/overseas-stock/v1/trading/inquire-present-balance` |
| 237 | REST | 해외주식 지정가체결내역조회 | `해외주식-070` | `TTTS6059R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/inquire-algo-ccnl` |
| 238 | REST | 해외주식 기간손익 | `v1_해외주식-032` | `TTTS3039R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/inquire-period-profit` |
| 239 | REST | 해외주식 매수가능금액조회 | `v1_해외주식-014` | `TTTS3007R` | `VTTS3007R` | GET | `/uapi/overseas-stock/v1/trading/inquire-psamount` |
| 240 | REST | 해외주식 정정취소주문 | `v1_해외주식-003` | `(미국 정정·취소) TTTT1004U (아시아 국가 하단 규격서 참고)` | `(미국 정정·취소) VTTT1004U (아시아 국가 하단 규격서 참고)` | POST | `/uapi/overseas-stock/v1/trading/order-rvsecncl` |
| 241 | REST | 해외주식 예약주문접수 | `v1_해외주식-002` | `(미국예약매수) TTTT3014U  (미국예약매도) TTTT3016U   (중국/홍콩/일본/베트남 예약주문) TTTS3013U` | `(미국예약매수) VTTT3014U  (미국예약매도) VTTT3016U   (중국/홍콩/일본/베트남 예약주문) VTTS3013U` | POST | `/uapi/overseas-stock/v1/trading/order-resv` |
| 242 | REST | 해외주식 미체결내역 | `v1_해외주식-005` | `TTTS3018R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/inquire-nccs` |
| 243 | REST | 해외주식 미국주간정정취소 | `v1_해외주식-027` | `TTTS6038U` | `모의투자 미지원` | POST | `/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl` |
| 244 | REST | 해외주식 주문체결내역 | `v1_해외주식-007` | `TTTS3035R` | `VTTS3035R` | GET | `/uapi/overseas-stock/v1/trading/inquire-ccnl` |
| 245 | REST | 해외주식 결제기준잔고 | `해외주식-064` | `CTRP6010R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance` |
| 246 | REST | 해외주식 일별거래내역 | `해외주식-063` | `CTOS4001R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/inquire-period-trans` |
| 247 | REST | 해외주식 미국주간주문 | `v1_해외주식-026` | `(주간매수) TTTS6036U (주간매도) TTTS6037U` | `모의투자 미지원` | POST | `/uapi/overseas-stock/v1/trading/daytime-order` |
| 248 | REST | 해외주식 예약주문조회 | `v1_해외주식-013` | `(미국) TTTT3039R (일본/중국/홍콩/베트남) TTTS3014R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/order-resv-list` |
| 249 | REST | 해외주식 주문 | `v1_해외주식-001` | `(미국매수) TTTT1002U  (미국매도) TTTT1006U (아시아 국가 하단 규격서 참고)` | `(미국매수) VTTT1002U  (미국매도) VTTT1001U  (아시아 국가 하단 규격서 참고)` | POST | `/uapi/overseas-stock/v1/trading/order` |
| 250 | REST | 해외주식 예약주문접수취소 | `v1_해외주식-004` | `(미국 예약주문 취소접수) TTTT3017U (아시아국가 미제공)` | `(미국 예약주문 취소접수) VTTT3017U (아시아국가 미제공)` | POST | `/uapi/overseas-stock/v1/trading/order-resv-ccnl` |
| 251 | REST | 해외주식 지정가주문번호조회 | `해외주식-071` | `TTTS6058R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/algo-ordno` |
| 252 | REST | 해외증거금 통화별조회 | `해외주식-035` | `TTTC2101R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/trading/foreign-margin` |

### [해외주식] 기본시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 253 | REST | 해외주식 체결추이 | `해외주식-037` | `HHDFS76200300` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/inquire-ccnl` |
| 254 | REST | 해외주식 기간별시세 | `v1_해외주식-010` | `HHDFS76240000` | `HHDFS76240000` | GET | `/uapi/overseas-price/v1/quotations/dailyprice` |
| 255 | REST | 해외결제일자조회 | `해외주식-017` | `CTOS5011R` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/quotations/countries-holiday` |
| 256 | REST | 해외주식 현재체결가 | `v1_해외주식-009` | `HHDFS00000300` | `HHDFS00000300` | GET | `/uapi/overseas-price/v1/quotations/price` |
| 257 | REST | 해외주식 복수종목 시세조회 | `해외주식 복수종목 시세조회` | `HHDFS76220000` | `미지원` | GET | `/uapi/overseas-price/v1/quotations/multprice` |
| 258 | REST | 해외주식조건검색 | `v1_해외주식-015` | `HHDFS76410000` | `HHDFS76410000` | GET | `/uapi/overseas-price/v1/quotations/inquire-search` |
| 259 | REST | 해외주식 상품기본정보 | `v1_해외주식-034` | `CTPF1702R` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/search-info` |
| 260 | REST | 해외지수분봉조회 | `v1_해외주식-031` | `FHKST03030200` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice` |
| 261 | REST | 해외주식분봉조회 | `v1_해외주식-030` | `HHDFS76950200` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice` |
| 262 | REST | 해외주식 현재가상세 | `v1_해외주식-029` | `HHDFS76200200` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/price-detail` |
| 263 | REST | 해외주식 업종별코드조회 | `해외주식-049` | `HHDFS76370100` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/industry-price` |
| 264 | REST | 해외주식 종목/지수/환율기간별시세(일/주/월/년) | `v1_해외주식-012` | `FHKST03030100` | `FHKST03030100` | GET | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` |
| 265 | REST | 해외주식 업종별시세 | `해외주식-048` | `HHDFS76370000` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/industry-theme` |
| 266 | REST | 해외주식 현재가 호가 | `해외주식-033` | `HHDFS76200100` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/inquire-asking-price` |

### [해외주식] 시세분석

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 267 | REST | 해외주식 거래증가율순위 | `해외주식-045` | `HHDFS76330000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/trade-growth` |
| 268 | REST | 해외주식 기간별권리조회 | `해외주식-052` | `CTRGT011R` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/period-rights` |
| 269 | REST | 해외주식 가격급등락 | `해외주식-038` | `HHDFS76260000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/price-fluct` |
| 270 | REST | 해외주식 거래대금순위 | `해외주식-044` | `HHDFS76320010` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/trade-pbmn` |
| 271 | REST | 해외주식 거래량급증 | `해외주식-039` | `HHDFS76270000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/volume-surge` |
| 272 | REST | 해외주식 신고/신저가 | `해외주식-042` | `HHDFS76300000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/new-highlow` |
| 273 | REST | 해외주식 매수체결강도상위 | `해외주식-040` | `HHDFS76280000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/volume-power` |
| 274 | REST | 해외주식 거래회전율순위 | `해외주식-046` | `HHDFS76340000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/trade-turnover` |
| 275 | REST | 해외뉴스종합(제목) | `해외주식-053` | `HHPSTH60100C1` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/news-title` |
| 276 | REST | 당사 해외주식담보대출 가능 종목 | `해외주식-051` | `CTLN4050R` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/colable-by-company` |
| 277 | REST | 해외주식 시가총액순위 | `해외주식-047` | `HHDFS76350100` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/market-cap` |
| 278 | REST | 해외속보(제목) | `해외주식-055` | `FHKST01011801` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/brknews-title` |
| 279 | REST | 해외주식 상승율/하락율 | `해외주식-041` | `HHDFS76290000` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/updown-rate` |
| 280 | REST | 해외주식 권리종합 | `해외주식-050` | `HHDFS78330900` | `모의투자 미지원` | GET | `/uapi/overseas-price/v1/quotations/rights-by-ice` |
| 281 | REST | 해외주식 거래량순위 | `해외주식-043` | `HHDFS76310010` | `모의투자 미지원` | GET | `/uapi/overseas-stock/v1/ranking/trade-vol` |

### [해외주식] 실시간시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 282 | WEBSOCKET | 해외주식 실시간호가 | `실시간-021` | `HDFSASP0` | `모의투자 미지원` | POST | `/tryitout/HDFSASP0` |
| 283 | WEBSOCKET | 해외주식 지연호가(아시아) | `실시간-008` | `HDFSASP1` | `모의투자 미지원` | POST | `/tryitout/HDFSASP1` |
| 284 | WEBSOCKET | 해외주식 실시간지연체결가 | `실시간-007` | `HDFSCNT0` | `모의투자 미지원` | POST | `/tryitout/HDFSCNT0` |
| 285 | WEBSOCKET | 해외주식 실시간체결통보 | `실시간-009` | `H0GSCNI0` | `H0GSCNI9` | POST | `/tryitout/H0GSCNI0` |

### [해외선물옵션] 주문/계좌

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 286 | REST | 해외선물옵션 주문 | `v1_해외선물-001` | `OTFM3001U` | `모의투자 미지원` | POST | `/uapi/overseas-futureoption/v1/trading/order` |
| 287 | REST | 해외선물옵션 정정취소주문 | `v1_해외선물-002, 003` | `(정정) OTFM3002U (취소) OTFM3003U` | `모의투자 미지원` | POST | `/uapi/overseas-futureoption/v1/trading/order-rvsecncl` |
| 288 | REST | 해외선물옵션 당일주문내역조회 | `v1_해외선물-004` | `OTFM3116R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-ccld` |
| 289 | REST | 해외선물옵션 미결제내역조회(잔고) | `v1_해외선물-005` | `OTFM1412R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-unpd` |
| 290 | REST | 해외선물옵션 주문가능조회 | `v1_해외선물-006` | `OTFM3304R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-psamount` |
| 291 | REST | 해외선물옵션 기간계좌손익 일별 | `해외선물-010` | `OTFM3118R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-ccld` |
| 292 | REST | 해외선물옵션 일별 체결내역 | `해외선물-011` | `OTFM3122R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld` |
| 293 | REST | 해외선물옵션 예수금현황 | `해외선물-012` | `OTFM1411R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-deposit` |
| 294 | REST | 해외선물옵션 일별 주문내역 | `해외선물-013` | `OTFM3120R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-daily-order` |
| 295 | REST | 해외선물옵션 기간계좌거래내역 | `해외선물-014` | `OTFM3114R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/inquire-period-trans` |
| 296 | REST | 해외선물옵션 증거금상세 | `해외선물-032` | `OTFM3115R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/trading/margin-detail` |

### [해외선물옵션] 기본시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 297 | REST | 해외선물종목현재가 | `v1_해외선물-009` | `HHDFC55010000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-price` |
| 298 | REST | 해외선물종목상세 | `v1_해외선물-008` | `HHDFC55010100` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/stock-detail` |
| 299 | REST | 해외선물 호가 | `해외선물-031` | `HHDFC86000000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-asking-price` |
| 300 | REST | 해외선물 분봉조회 | `해외선물-016` | `HHDFC55020400` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-futurechartprice` |
| 301 | REST | 해외선물 체결추이(틱) | `해외선물-019` | `HHDFC55020200` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/tick-ccnl` |
| 302 | REST | 해외선물 체결추이(주간) | `해외선물-017` | `HHDFC55020000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/weekly-ccnl` |
| 303 | REST | 해외선물 체결추이(일간) | `해외선물-018` | `HHDFC55020100` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/daily-ccnl` |
| 304 | REST | 해외선물 체결추이(월간) | `해외선물-020` | `HHDFC55020300` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/monthly-ccnl` |
| 305 | REST | 해외선물 상품기본정보 | `해외선물-023` | `HHDFC55200000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/search-contract-detail` |
| 306 | REST | 해외선물 미결제추이 | `해외선물-029` | `HHDDB95030000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/investor-unpd-trend` |
| 307 | REST | 해외옵션종목현재가 | `해외선물-035` | `HHDFO55010000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-price` |
| 308 | REST | 해외옵션종목상세 | `해외선물-034` | `HHDFO55010100` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-detail` |
| 309 | REST | 해외옵션 호가 | `해외선물-033` | `HHDFO86000000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-asking-price` |
| 310 | REST | 해외옵션 분봉조회 | `해외선물-040` | `HHDFO55020400` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/inquire-time-optchartprice` |
| 311 | REST | 해외옵션 체결추이(틱) | `해외선물-038` | `HHDFO55020200` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-tick-ccnl` |
| 312 | REST | 해외옵션 체결추이(일간) | `해외선물-037` | `HHDFO55020100` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-daily-ccnl` |
| 313 | REST | 해외옵션 체결추이(주간) | `해외선물-036` | `HHDFO55020000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-weekly-ccnl` |
| 314 | REST | 해외옵션 체결추이(월간) | `해외선물-039` | `HHDFO55020300` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/opt-monthly-ccnl` |
| 315 | REST | 해외옵션 상품기본정보 | `해외선물-041` | `HHDFO55200000` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/search-opt-detail` |
| 316 | REST | 해외선물옵션 장운영시간 | `해외선물-030` | `OTFM2229R` | `모의투자 미지원` | GET | `/uapi/overseas-futureoption/v1/quotations/market-time` |

### [해외선물옵션]실시간시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 317 | WEBSOCKET | 해외선물옵션 실시간체결가 | `실시간-017` | `HDFFF020` | `모의투자 미지원` | POST | `/tryitout/HDFFF020` |
| 318 | WEBSOCKET | 해외선물옵션 실시간호가 | `실시간-018` | `HDFFF010` | `모의투자 미지원` | POST | `/tryitout/HDFFF010` |
| 319 | WEBSOCKET | 해외선물옵션 실시간주문내역통보 | `실시간-019` | `HDFFF1C0` | `모의투자 미지원` | POST | `/tryitout/HDFFF1C0` |
| 320 | WEBSOCKET | 해외선물옵션 실시간체결내역통보 | `실시간-020` | `HDFFF2C0` | `모의투자 미지원` | POST | `/tryitout/HDFFF2C0` |

### [장내채권] 주문/계좌

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 321 | REST | 장내채권 매수주문 | `국내주식-124` | `TTTC0952U` | `모의투자 미지원` | POST | `/uapi/domestic-bond/v1/trading/buy` |
| 322 | REST | 장내채권 매도주문 | `국내주식-123` | `TTTC0958U` | `모의투자 미지원` | POST | `/uapi/domestic-bond/v1/trading/sell` |
| 323 | REST | 장내채권 정정취소주문 | `국내주식-125` | `TTTC0953U` | `모의투자 미지원` | POST | `/uapi/domestic-bond/v1/trading/order-rvsecncl` |
| 324 | REST | 채권정정취소가능주문조회 | `국내주식-126` | `CTSC8035R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl` |
| 325 | REST | 장내채권 주문체결내역 | `국내주식-127` | `CTSC8013R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/trading/inquire-daily-ccld` |
| 326 | REST | 장내채권 잔고조회 | `국내주식-198` | `CTSC8407R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/trading/inquire-balance` |
| 327 | REST | 장내채권 매수가능조회 | `국내주식-199` | `TTTC8910R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/trading/inquire-psbl-order` |

### [장내채권] 기본시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 328 | REST | 장내채권현재가(호가) | `국내주식-132` | `FHKBJ773401C0` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/inquire-asking-price` |
| 329 | REST | 장내채권현재가(시세) | `국내주식-200` | `FHKBJ773400C0` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/inquire-price` |
| 330 | REST | 장내채권현재가(체결) | `국내주식-201` | `FHKBJ773403C0` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/inquire-ccnl` |
| 331 | REST | 장내채권현재가(일별) | `국내주식-202` | `FHKBJ773404C0` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-price` |
| 332 | REST | 장내채권 기간별시세(일) | `국내주식-159` | `FHKBJ773701C0` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice` |
| 333 | REST | 장내채권 평균단가조회 | `국내주식-158` | `CTPF2005R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/avg-unit` |
| 334 | REST | 장내채권 발행정보 | `국내주식-156` | `CTPF1101R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/issue-info` |
| 335 | REST | 장내채권 기본조회 | `국내주식-129` | `CTPF1114R` | `모의투자 미지원` | GET | `/uapi/domestic-bond/v1/quotations/search-bond-info` |

### [장내채권] 실시간시세

| # | 방식 | API 명 | API ID | 실전 TR_ID | 모의 TR_ID | Method | URL |
|---|------|--------|--------|-----------|-----------|--------|-----|
| 336 | WEBSOCKET | 일반채권 실시간체결가 | `실시간-052` | `H0BJCNT0` | `모의투자 미지원` | POST | `/tryitout/H0BJCNT0` |
| 337 | WEBSOCKET | 일반채권 실시간호가 | `실시간-053` | `H0BJCNT0` | `모의투자 미지원` | POST | `/tryitout/H0BJASP0` |
| 338 | WEBSOCKET | 채권지수 실시간체결가 | `실시간-060` | `H0BICNT0` | `모의투자 미지원` | POST | `/tryitout/H0BICNT0` |

---

## 프로젝트 사용 API 상세

> ⭐ 표시: 현재 portfolio 프로젝트에서 실제 사용 중인 API

## Hashkey

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `Hashkey` |
| HTTP Method | `POST` |
| URL 명 | `/uapi/hashkey` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

해쉬키(Hashkey)는 보안을 위한 요소로 사용자가 보낸 요청 값을 중간에 탈취하여 변조하지 못하도록 하는데 사용됩니다.
해쉬키를 사용하면 POST로 보내는 요청(주로 주문/정정/취소 API 해당)의 body 값을 사전에 암호화시킬 수 있습니다.
해쉬키는 비필수값으로 사용하지 않아도 POST API 호출은 가능합니다.

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |

### Request Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `JsonBody` | 요청값 | object | Y |  | POST로 보낼 body값 /  / ex) / datas = { /     "CANO": '00000000', /     "ACNT_PRDT_CD": "01", /     "OVRS_EXCG_CD": "SHAA" /  } |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `JsonBody` | 요청값 | object | Y |  | 요청한 JsonBody |
| `HASH` | 해쉬키 | string | Y | 256 | [POST API 대상] Client가 요청하는 Request Body를 hashkey api로 생성한 Hash값 / * API문서 > hashkey 참조 |

### Request 예시

```json
{
	"ORD_PRCS_DVSN_CD": "02",
	"CANO": "계좌번호",
	"ACNT_PRDT_CD": "03",
	"SLL_BUY_DVSN_CD": "02",
	"SHTN_PDNO": "101S06",
	"ORD_QTY": "1",
	"UNIT_PRICE": "370",
	"NMPR_TYPE_CD": "",
	"KRX_NMPR_CNDT_CD": "",
	"CTAC_TLNO": "",
	"FUOP_ITEM_DVSN_CD": "",
	"ORD_DVSN_CD": "02"
}
```

### Response 예시

```json
{
  "BODY": {
    "ORD_PRCS_DVSN_CD": "02",
    "CANO": "계좌번호",
    "ACNT_PRDT_CD": "03",
    "SLL_BUY_DVSN_CD": "02",
    "SHTN_PDNO": "101S06",
    "ORD_QTY": "1",
    "UNIT_PRICE": "370",
    "NMPR_TYPE_CD": "",
    "KRX_NMPR_CNDT_CD": "",
    "CTAC_TLNO": "",
    "FUOP_ITEM_DVSN_CD": "",
    "ORD_DVSN_CD": "02"
  },
  "HASH": "8b84068222a49302f7ef58226d90403f62e216828f8103465f900de0e7be2f0f"
}
```

---

## 주식현재가 시세

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `v1_국내주식-008` |
| 실전 TR_ID | `FHKST01010100` |
| 모의 TR_ID | `FHKST01010100` |
| HTTP Method | `GET` |
| URL 명 | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

주식 현재가 시세 API입니다. 실시간 시세를 원하신다면 웹소켓 API를 활용하세요.

※ 종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
   https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  / 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  / 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| `tr_id` | 거래ID | string | Y | 13 | FHKST01010100 |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| `custtype` | 고객 타입 | string | Y | 1 | B : 법인  / P : 개인 |
| `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
| `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  / ex) 01011112222 (하이픈 등 구분값 제거) |
| `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Request Query Parameter

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `FID_COND_MRKT_DIV_CODE` | 조건 시장 분류 코드 | string | Y | 2 | J:KRX, NX:NXT, UN:통합 |
| `FID_INPUT_ISCD` | 입력 종목코드 | string | Y | 12 | 종목코드 (ex 005930 삼성전자)  // ETN은 종목코드 6자리 앞에 Q 입력 필수 |

### Response Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
| `msg_cd` | 응답코드 | string | Y | 8 |  |
| `msg1` | 응답메세지 | string | Y | 80 |  |
| `output` | 응답상세 | object | Y |  |  |
| `iscd_stat_cls_code` | 종목 상태 구분 코드 | string | Y | 3 | 51 : 관리종목 / 52 : 투자위험 / 53 : 투자경고 / 54 : 투자주의 / 55 : 신용가능 / 57 : 증거금 100% / 58 : 거래정지 / 59 : 단기과열종목 |
| `marg_rate` | 증거금 비율 | string | Y | 84 |  |
| `rprs_mrkt_kor_name` | 대표 시장 한글 명 | string | Y | 40 |  |
| `new_hgpr_lwpr_cls_code` | 신 고가 저가 구분 코드 | string | Y | 10 |  |
| `bstp_kor_isnm` | 업종 한글 종목명 | string | Y | 40 |  |
| `temp_stop_yn` | 임시 정지 여부 | string | Y | 1 |  |
| `oprc_rang_cont_yn` | 시가 범위 연장 여부 | string | Y | 1 |  |
| `clpr_rang_cont_yn` | 종가 범위 연장 여부 | string | Y | 1 |  |
| `crdt_able_yn` | 신용 가능 여부 | string | Y | 1 |  |
| `grmn_rate_cls_code` | 보증금 비율 구분 코드 | string | Y | 3 |  |
| `elw_pblc_yn` | ELW 발행 여부 | string | Y | 1 |  |
| `stck_prpr` | 주식 현재가 | string | Y | 10 |  |
| `prdy_vrss` | 전일 대비 | string | Y | 10 |  |
| `prdy_vrss_sign` | 전일 대비 부호 | string | Y | 1 |  |
| `prdy_ctrt` | 전일 대비율 | string | Y | 82 |  |
| `acml_tr_pbmn` | 누적 거래 대금 | string | Y | 18 |  |
| `acml_vol` | 누적 거래량 | string | Y | 18 |  |
| `prdy_vrss_vol_rate` | 전일 대비 거래량 비율 | string | Y | 84 |  |
| `stck_oprc` | 주식 시가2 | string | Y | 10 |  |
| `stck_hgpr` | 주식 최고가 | string | Y | 10 |  |
| `stck_lwpr` | 주식 최저가 | string | Y | 10 |  |
| `stck_mxpr` | 주식 상한가 | string | Y | 10 |  |
| `stck_llam` | 주식 하한가 | string | Y | 10 |  |
| `stck_sdpr` | 주식 기준가 | string | Y | 10 |  |
| `wghn_avrg_stck_prc` | 가중 평균 주식 가격 | string | Y | 192 |  |
| `hts_frgn_ehrt` | HTS 외국인 소진율 | string | Y | 82 |  |
| `frgn_ntby_qty` | 외국인 순매수 수량 | string | Y | 12 |  |
| `pgtr_ntby_qty` | 프로그램매매 순매수 수량 | string | Y | 18 |  |
| `pvt_scnd_dmrs_prc` | 피벗 2차 디저항 가격 | string | Y | 10 |  |
| `pvt_frst_dmrs_prc` | 피벗 1차 디저항 가격 | string | Y | 10 |  |
| `pvt_pont_val` | 피벗 포인트 값 | string | Y | 10 |  |
| `pvt_frst_dmsp_prc` | 피벗 1차 디지지 가격 | string | Y | 10 |  |
| `pvt_scnd_dmsp_prc` | 피벗 2차 디지지 가격 | string | Y | 10 |  |
| `dmrs_val` | 디저항 값 | string | Y | 10 |  |
| `dmsp_val` | 디지지 값 | string | Y | 10 |  |
| `cpfn` | 자본금 | string | Y | 22 |  |
| `rstc_wdth_prc` | 제한 폭 가격 | string | Y | 10 |  |
| `stck_fcam` | 주식 액면가 | string | Y | 11 |  |
| `stck_sspr` | 주식 대용가 | string | Y | 10 |  |
| `aspr_unit` | 호가단위 | string | Y | 10 |  |
| `hts_deal_qty_unit_val` | HTS 매매 수량 단위 값 | string | Y | 10 |  |
| `lstn_stcn` | 상장 주수 | string | Y | 18 |  |
| `hts_avls` | HTS 시가총액 | string | Y | 18 |  |
| `per` | PER | string | Y | 82 |  |
| `pbr` | PBR | string | Y | 82 |  |
| `stac_month` | 결산 월 | string | Y | 2 |  |
| `vol_tnrt` | 거래량 회전율 | string | Y | 82 |  |
| `eps` | EPS | string | Y | 112 |  |
| `bps` | BPS | string | Y | 112 |  |
| `d250_hgpr` | 250일 최고가 | string | Y | 10 |  |
| `d250_hgpr_date` | 250일 최고가 일자 | string | Y | 8 |  |
| `d250_hgpr_vrss_prpr_rate` | 250일 최고가 대비 현재가 비율 | string | Y | 84 |  |
| `d250_lwpr` | 250일 최저가 | string | Y | 10 |  |
| `d250_lwpr_date` | 250일 최저가 일자 | string | Y | 8 |  |
| `d250_lwpr_vrss_prpr_rate` | 250일 최저가 대비 현재가 비율 | string | Y | 84 |  |
| `stck_dryy_hgpr` | 주식 연중 최고가 | string | Y | 10 |  |
| `dryy_hgpr_vrss_prpr_rate` | 연중 최고가 대비 현재가 비율 | string | Y | 84 |  |
| `dryy_hgpr_date` | 연중 최고가 일자 | string | Y | 8 |  |
| `stck_dryy_lwpr` | 주식 연중 최저가 | string | Y | 10 |  |
| `dryy_lwpr_vrss_prpr_rate` | 연중 최저가 대비 현재가 비율 | string | Y | 84 |  |
| `dryy_lwpr_date` | 연중 최저가 일자 | string | Y | 8 |  |
| `w52_hgpr` | 52주일 최고가 | string | Y | 10 |  |
| `w52_hgpr_vrss_prpr_ctrt` | 52주일 최고가 대비 현재가 대비 | string | Y | 82 |  |
| `w52_hgpr_date` | 52주일 최고가 일자 | string | Y | 8 |  |
| `w52_lwpr` | 52주일 최저가 | string | Y | 10 |  |
| `w52_lwpr_vrss_prpr_ctrt` | 52주일 최저가 대비 현재가 대비 | string | Y | 82 |  |
| `w52_lwpr_date` | 52주일 최저가 일자 | string | Y | 8 |  |
| `whol_loan_rmnd_rate` | 전체 융자 잔고 비율 | string | Y | 84 |  |
| `ssts_yn` | 공매도가능여부 | string | Y | 1 |  |
| `stck_shrn_iscd` | 주식 단축 종목코드 | string | Y | 9 |  |
| `fcam_cnnm` | 액면가 통화명 | string | Y | 20 |  |
| `cpfn_cnnm` | 자본금 통화명 | string | Y | 20 |  |
| `apprch_rate` | 접근도 | string | Y | 112 |  |
| `frgn_hldn_qty` | 외국인 보유 수량 | string | Y | 18 |  |
| `vi_cls_code` | VI적용구분코드 | string | Y | 1 |  |
| `ovtm_vi_cls_code` | 시간외단일가VI적용구분코드 | string | Y | 1 |  |
| `last_ssts_cntg_qty` | 최종 공매도 체결 수량 | string | Y | 12 |  |
| `invt_caful_yn` | 투자유의여부 | string | Y | 1 |  |
| `mrkt_warn_cls_code` | 시장경고코드 | string | Y | 2 |  |
| `short_over_yn` | 단기과열여부 | string | Y | 1 |  |
| `sltr_yn` | 정리매매여부 | string | Y | 1 |  |
| `mang_issu_cls_code` | 관리종목여부 | string | Y | 1 |  |

### Request 예시

```json
{
"fid_cond_mrkt_div_code": "J",
"fid_input_iscd": "000660"
}
```

### Response 예시

```json
{
  "output": {
    "iscd_stat_cls_code": "55",
    "marg_rate": "20.00",
    "rprs_mrkt_kor_name": "KOSPI200",
    "bstp_kor_isnm": "전기.전자",
    "temp_stop_yn": "N",
    "oprc_rang_cont_yn": "N",
    "clpr_rang_cont_yn": "N",
    "crdt_able_yn": "Y",
    "grmn_rate_cls_code": "40",
    "elw_pblc_yn": "Y",
    "stck_prpr": "128500",
    "prdy_vrss": "0",
    "prdy_vrss_sign": "3",
    "prdy_ctrt": "0.00",
    "acml_tr_pbmn": "344570137500",
    "acml_vol": "2669075",
    "prdy_vrss_vol_rate": "75.14",
    "stck_oprc": "128500",
    "stck_hgpr": "130000",
    "stck_lwpr": "128500",
    "stck_mxpr": "167000",
    "stck_llam": "90000",
    "stck_sdpr": "128500",
    "wghn_avrg_stck_prc": "129097.23",
    "hts_frgn_ehrt": "49.48",
    "frgn_ntby_qty": "0",
    "pgtr_ntby_qty": "287715",
    "pvt_scnd_dmrs_prc": "131833",
    "pvt_frst_dmrs_prc": "130166",
    "pvt_pont_val": "128333",
    "pvt_frst_dmsp_prc": "126666",
    "pvt_scnd_dmsp_prc": "124833",
    "dmrs_val": "129250",
    "dmsp_val": "125750",
    "cpfn": "36577",
    "rstc_wdth_prc": "38500",
    "stck_fcam": "5000",
    "stck_sspr": "97660",
    "aspr_unit": "500",
    "hts_deal_qty_unit_val": "1",
    "lstn_stcn": "728002365",
    "hts_avls": "935483",
    "per": "19.67",
    "pbr": "1.72",
    "stac_month": "12",
    "vol_tnrt": "0.37",
    "eps": "6532.00",
    "bps": "74721.00",
    "d250_hgpr": "149500",
    "d250_hgpr_date": "20210225",
    "d250_hgpr_vrss_prpr_rate": "-14.05",
    "d250_lwpr": "90500",
    "d250_lwpr_date": "20211013",
    "d250_lwpr_vrss_prpr_rate": "41.99",
    "stck_dryy_hgpr": "132500",
    "dryy_hgpr_vrss_prpr_rate": "-3.02",
    "dryy_hgpr_date": "20220103",
    "stck_dryy_lwpr": "121500",
    "dryy_lwpr_vrss_prpr_rate": "5.76",
    "dryy_lwpr_date": "20220105",
    "w52_hgpr": "149500",
    "w52_hgpr_vrss_prpr_ctrt": "-14.05",
    "w52_hgpr_date": "20210225",
    "w52_lwpr": "90500",
    "w52_lwpr_vrss_prpr_ctrt": "41.99",
    "w52_lwpr_date": "20211013",
    "whol_loan_rmnd_rate": "0.22",
    "ssts_yn": "Y",
    "stck_shrn_iscd": "000660",
    "fcam_cnnm": "5,000",
    "cpfn_cnnm": "36,576 억",
    "frgn_hldn_qty": "360220601",
    "vi_cls_code": "N",
    "ovtm_vi_cls_code": "N",
    "last_ssts_cntg_qty": "43916",
    "invt_caful_yn": "N",
    "mrkt_warn_cls_code": "00",
    "short_over_yn": "N",
    "sltr_yn": "N"
  },
  "rt_cd": "0",
  "msg_cd": "MCA00000",
  "msg1": "정상처리 되었습니다!"
}
```

---

## 주식주문(정정취소)

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `v1_국내주식-003` |
| 실전 TR_ID | `TTTC0013U` |
| 모의 TR_ID | `VTTC0013U` |
| HTTP Method | `POST` |
| URL 명 | `/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

주문 건에 대하여 정정 및 취소하는 API입니다. 단, 이미 체결된 건은 정정 및 취소가 불가합니다.

※ 정정은 원주문에 대한 주문단가 혹은 주문구분을 변경하는 사항으로, 정정이 가능한 수량은 원주문수량을 초과 할 수 없습니다.

※ 주식주문(정정취소) 호출 전에 반드시 주식정정취소가능주문조회 호출을 통해 정정취소가능수량(output &gt; psbl_qty)을 확인하신 후 정정취소주문 내시기 바랍니다.

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  / 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  / 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) /  / ※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출 / EX) "Bearer eyJ..........8GA" |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| `tr_id` | 거래ID | string | Y | 13 | ※ 구TR은 사전고지 없이 막힐 수 있으므로 반드시 신TR로 변경이용 부탁드립니다. / [실전투자] / 정정/취소 (구)TTTC0803U → (신)TTTC0013U / 정정/취소 (모의투자) (구)VTTC0803U → (신)VTTC0013U |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| `custtype` | 고객 타입 | string | Y | 1 | B : 법인  / P : 개인 |
| `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
| `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  / ex) 01011112222 (하이픈 등 구분값 제거) |
| `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Request Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `CANO` | 종합계좌번호 | string | Y | 8 | 종합계좌번호 |
| `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 상품유형코드 |
| `KRX_FWDG_ORD_ORGNO` | 한국거래소전송주문조직번호 | string | Y | 5 |  |
| `ORGN_ODNO` | 원주문번호 | string | Y | 10 | 원주문번호 |
| `ORD_DVSN` | 주문구분 | string | Y | 2 | [KRX] / 00 : 지정가 / 01 : 시장가 / 02 : 조건부지정가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 05 : 장전 시간외 / 06 : 장후 시간외 / 07 : 시간외 단일가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) / 21 : 중간가 / 22 : 스톱지정가 / 23 : 중간가IOC / 24 : 중간가FOK /  / [NXT] / 00 : 지정가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) / 21 : 중간가 / 22 : 스톱지정가 / 23 : 중간가IOC / 24 : 중간가FOK /  / [SOR] / 00 : 지정가 / 01 : 시장가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) |
| `RVSE_CNCL_DVSN_CD` | 정정취소구분코드 | string | Y | 2 | 01@정정 / 02@취소 |
| `ORD_QTY` | 주문수량 | string | Y | 10 | 주문수량 |
| `ORD_UNPR` | 주문단가 | string | Y | 19 | 주문단가 |
| `QTY_ALL_ORD_YN` | 잔량전부주문여부 | string | Y | 1 | 'Y@전량 / N@일부' |
| `CNDT_PRIC` | 조건가격 | string | N | 19 | 스탑지정가호가에서 사용 |
| `EXCG_ID_DVSN_CD` | 거래소ID구분코드 | string | N | 3 | 한국거래소 : KRX / 대체거래소 (넥스트레이드) : NXT / SOR (Smart Order Routing) : SOR / → 미입력시 KRX로 진행되며, 모의투자는 KRX만 가능 |

### Response Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
| `msg_cd` | 응답코드 | string | Y | 8 |  |
| `msg1` | 응답메세지 | string | Y | 80 |  |
| `output` | 응답상세 | object array | Y |  | single |
| `krx_fwdg_ord_orgno` | 한국거래소전송주문조직번호 | string | Y | 5 |  |
| `odno` | 주문번호 | string | Y | 10 |  |
| `ord_tmd` | 주문시각 | string | Y | 6 |  |

### Request 예시

```json
{
"CANO": "810XXXXX",
"ACNT_PRDT_CD": "01",
"KRX_FWDG_ORD_ORGNO": "",
"ORGN_ODNO": "0001566017",
"ORD_DVSN": "00",
"RVSE_CNCL_DVSN_CD": "01",
"ORD_QTY": "1",
"ORD_UNPR": "180000",
"QTY_ALL_ORD_YN": "N"
}
```

### Response 예시

```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "06010",
    "ODNO": "0001569139",
    "ORD_TMD": "131438"
  }
}
```

---

## 주식잔고조회

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `v1_국내주식-006` |
| 실전 TR_ID | `TTTC8434R` |
| 모의 TR_ID | `VTTC8434R` |
| HTTP Method | `GET` |
| URL 명 | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

주식 잔고조회 API입니다. 
실전계좌의 경우, 한 번의 호출에 최대 50건까지 확인 가능하며, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 
모의계좌의 경우, 한 번의 호출에 최대 20건까지 확인 가능하며, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 

* 당일 전량매도한 잔고도 보유수량 0으로 보여질 수 있으나, 해당 보유수량 0인 잔고는 최종 D-2일 이후에는 잔고에서 사라집니다.

※ 중요 : 해당 API는 제공 정보량이 많아 조회속도가 느린 API입니다. 주문 준비를 위해서는 주식매수/매도가능수량 조회 TR 사용을 권장 드립니다.

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | N | 40 | application/json; charset=utf-8 |
| `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token / 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용) / 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |
| `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| `tr_id` | 거래ID | string | Y | 13 | [실전투자] / TTTC8434R : 주식 잔고 조회 /  / [모의투자] / VTTC8434R : 주식 잔고 조회 |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회 / N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| `custtype` | 고객타입 | string | N | 1 | B : 법인 / P : 개인 |
| `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
| `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호 / ex) 01011112222 (하이픈 등 구분값 제거) |
| `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Request Query Parameter

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `CANO` | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| `AFHR_FLPR_YN` | 시간외단일가, 거래소여부 | string | Y | 1 | N : 기본값, / Y : 시간외단일가, / X : NXT 정규장 (프리마켓, 메인, 애프터마켓) / ※ NXT 선택 시 : NXT 거래종목만 시세 등 정보가 NXT 기준으로 변동됩니다. KRX 종목들은 그대로 유지 |
| `OFL_YN` | 오프라인여부 | string | N | 1 | 공란(Default) |
| `INQR_DVSN` | 조회구분 | string | Y | 2 | 01 : 대출일별 |
| `UNPR_DVSN` | 단가구분 | string | Y | 2 | 01 : 기본값 |
| `FUND_STTL_ICLD_YN` | 펀드결제분포함여부 | string | Y | 1 | N : 포함하지 않음 / Y :  포함 |
| `FNCG_AMT_AUTO_RDPT_YN` | 융자금액자동상환여부 | string | Y | 1 | N : 기본값 |
| `PRCS_DVSN` | 처리구분 | string | Y | 2 | 00 :  전일매매포함 / 01 : 전일매매미포함 |
| `CTX_AREA_FK100` | 연속조회검색조건100 | string | N | 100 | 공란 : 최초 조회시 / 이전 조회 Output CTX_AREA_FK100 값 : 다음페이지 조회시(2번째부터) |
| `CTX_AREA_NK100` | 연속조회키100 | string | N | 100 | 공란 : 최초 조회시 / 이전 조회 Output CTX_AREA_NK100 값 : 다음페이지 조회시(2번째부터) |

### Response Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
| `tr_cont` | 연속 거래 여부 | string | Y | 1 | F or M : 다음 데이터 있음 / D or E : 마지막 데이터 |
| `gt_uid` | Global UID | string | Y | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `rt_cd` | 성공 실패 여부 | string | Y | 1 | 0 : 성공 / 0 이외의 값 : 실패 |
| `msg_cd` | 응답코드 | string | Y | 8 | 응답코드 |
| `msg1` | 응답메세지 | string | Y | 80 | 응답메세지 |
| `ctx_area_fk100` | 연속조회검색조건100 | string | Y | 100 |  |
| `ctx_area_nk100` | 연속조회키100 | string | Y | 100 |  |
| `output1` | 응답상세1 | object array | Y |  | Array |
| `pdno` | 상품번호 | string | Y | 12 | 종목번호(뒷 6자리) |
| `prdt_name` | 상품명 | string | Y | 60 | 종목명 |
| `trad_dvsn_name` | 매매구분명 | string | Y | 60 | 매수매도구분 |
| `bfdy_buy_qty` | 전일매수수량 | string | Y | 10 |  |
| `bfdy_sll_qty` | 전일매도수량 | string | Y | 10 |  |
| `thdt_buyqty` | 금일매수수량 | string | Y | 10 |  |
| `thdt_sll_qty` | 금일매도수량 | string | Y | 10 |  |
| `hldg_qty` | 보유수량 | string | Y | 19 |  |
| `ord_psbl_qty` | 주문가능수량 | string | Y | 10 |  |
| `pchs_avg_pric` | 매입평균가격 | string | Y | 22 | 매입금액 / 보유수량 |
| `pchs_amt` | 매입금액 | string | Y | 19 |  |
| `prpr` | 현재가 | string | Y | 19 |  |
| `evlu_amt` | 평가금액 | string | Y | 19 |  |
| `evlu_pfls_amt` | 평가손익금액 | string | Y | 19 | 평가금액 - 매입금액 |
| `evlu_pfls_rt` | 평가손익율 | string | Y | 9 |  |
| `evlu_erng_rt` | 평가수익율 | string | Y | 31 | 미사용항목(0으로 출력) |
| `loan_dt` | 대출일자 | string | Y | 8 | INQR_DVSN(조회구분)을 01(대출일별)로 설정해야 값이 나옴 |
| `loan_amt` | 대출금액 | string | Y | 19 |  |
| `stln_slng_chgs` | 대주매각대금 | string | Y | 19 |  |
| `expd_dt` | 만기일자 | string | Y | 8 |  |
| `fltt_rt` | 등락율 | string | Y | 31 |  |
| `bfdy_cprs_icdc` | 전일대비증감 | string | Y | 19 |  |
| `item_mgna_rt_name` | 종목증거금율명 | string | Y | 20 |  |
| `grta_rt_name` | 보증금율명 | string | Y | 20 |  |
| `sbst_pric` | 대용가격 | string | Y | 19 | 증권매매의 위탁보증금으로서 현금 대신에 사용되는 유가증권 가격 |
| `stck_loan_unpr` | 주식대출단가 | string | Y | 22 |  |
| `output2` | 응답상세2 | object array | Y |  | Array |
| `dnca_tot_amt` | 예수금총금액 | string | Y | 19 | 예수금 |
| `nxdy_excc_amt` | 익일정산금액 | string | Y | 19 | D+1 예수금 |
| `prvs_rcdl_excc_amt` | 가수도정산금액 | string | Y | 19 | D+2 예수금 |
| `cma_evlu_amt` | CMA평가금액 | string | Y | 19 |  |
| `bfdy_buy_amt` | 전일매수금액 | string | Y | 19 |  |
| `thdt_buy_amt` | 금일매수금액 | string | Y | 19 |  |
| `nxdy_auto_rdpt_amt` | 익일자동상환금액 | string | Y | 19 |  |
| `bfdy_sll_amt` | 전일매도금액 | string | Y | 19 |  |
| `thdt_sll_amt` | 금일매도금액 | string | Y | 19 |  |
| `d2_auto_rdpt_amt` | D+2자동상환금액 | string | Y | 19 |  |
| `bfdy_tlex_amt` | 전일제비용금액 | string | Y | 19 |  |
| `thdt_tlex_amt` | 금일제비용금액 | string | Y | 19 |  |
| `tot_loan_amt` | 총대출금액 | string | Y | 19 |  |
| `scts_evlu_amt` | 유가평가금액 | string | Y | 19 |  |
| `tot_evlu_amt` | 총평가금액 | string | Y | 19 | 유가증권 평가금액 합계금액 + D+2 예수금 |
| `nass_amt` | 순자산금액 | string | Y | 19 |  |
| `fncg_gld_auto_rdpt_yn` | 융자금자동상환여부 | string | Y | 1 | 보유현금에 대한 융자금만 차감여부 / 신용융자 매수체결 시점에서는 융자비율을 매매대금 100%로 계산 하였다가 수도결제일에 보증금에 해당하는 금액을 고객의 현금으로 충당하여 융자금을 감소시키는 업무 |
| `pchs_amt_smtl_amt` | 매입금액합계금액 | string | Y | 19 |  |
| `evlu_amt_smtl_amt` | 평가금액합계금액 | string | Y | 19 | 유가증권 평가금액 합계금액 |
| `evlu_pfls_smtl_amt` | 평가손익합계금액 | string | Y | 19 |  |
| `tot_stln_slng_chgs` | 총대주매각대금 | string | Y | 19 |  |
| `bfdy_tot_asst_evlu_amt` | 전일총자산평가금액 | string | Y | 19 |  |
| `asst_icdc_amt` | 자산증감액 | string | Y | 19 |  |
| `asst_icdc_erng_rt` | 자산증감수익율 | string | Y | 31 | 데이터 미제공 |

### Request 예시

```json
{
	"CANO": "810XXXXX",
	"ACNT_PRDT_CD": "01",
	"AFHR_FLPR_YN": "N",
	"OFL_YN": "",
	"INQR_DVSN": "01",
	"UNPR_DVSN": "01",
	"FUND_STTL_ICLD_YN": "N",
	"FNCG_AMT_AUTO_RDPT_YN": "N",
	"PRCS_DVSN": "01",
	"CTX_AREA_FK100": "",
	"CTX_AREA_NK100": ""
}
```

### Response 예시

```json
{
  "ctx_area_fk100": "81055689^01^N^N^01^01^N^                                                                            ",
  "ctx_area_nk100": "                                                                                                    ",
  "output1": [
    {
      "pdno": "009150",
      "prdt_name": "삼성전기",
      "trad_dvsn_name": "현금",
      "bfdy_buy_qty": "12",
      "bfdy_sll_qty": "0",
      "thdt_buyqty": "1686",
      "thdt_sll_qty": "41",
      "hldg_qty": "1657",
      "ord_psbl_qty": "1611",
      "pchs_avg_pric": "135440.2517",
      "pchs_amt": "224424497",
      "prpr": "0",
      "evlu_amt": "0",
      "evlu_pfls_amt": "0",
      "evlu_pfls_rt": "0.00",
      "evlu_erng_rt": "0.00000000",
      "loan_dt": "",
      "loan_amt": "0",
      "stln_slng_chgs": "0",
      "expd_dt": "",
      "fltt_rt": "-100.00000000",
      "bfdy_cprs_icdc": "-184500",
      "item_mgna_rt_name": "",
      "grta_rt_name": "",
      "sbst_pric": "140220",
      "stck_loan_unpr": "0.0000"
    },
    {
      "pdno": "009150",
      "prdt_name": "삼성전기",
      "trad_dvsn_name": "자기융자",
      "bfdy_buy_qty": "3",
      "bfdy_sll_qty": "0",
      "thdt_buyqty": "0",
      "thdt_sll_qty": "0",
      "hldg_qty": "3",
      "ord_psbl_qty": "3",
      "pchs_avg_pric": "123000.0000",
      "pchs_amt": "369000",
      "prpr": "0",
      "evlu_amt": "0",
      "evlu_pfls_amt": "0",
      "evlu_pfls_rt": "0.00",
      "evlu_erng_rt": "0.00000000",
      "loan_dt": "20211223",
      "loan_amt": "369000",
      "stln_slng_chgs": "0",
      "expd_dt": "",
      "fltt_rt": "-100.00000000",
      "bfdy_cprs_icdc": "-184500",
      "item_mgna_rt_name": "",
      "grta_rt_name": "",
      "sbst_pric": "140220",
      "stck_loan_unpr": "123000.0000"
    }
	  ],
  "output2": [
        {
            "dnca_tot_amt": "346455",
            "nxdy_excc_amt": "346455",
            "prvs_rcdl_excc_amt": "346455",
            "cma_evlu_amt": "0",
            "bfdy_buy_amt": "0",
            "thdt_buy_amt": "0",
            "nxdy_auto_rdpt_amt": "0",
            "bfdy_sll_amt": "0",
            "thdt_sll_amt": "0",
            "d2_auto_rdpt_amt": "0",
            "bfdy_tlex_amt": "0",
            "thdt_tlex_amt": "0",
            "tot_loan_amt": "0",
            "scts_evlu_amt": "1759600",
            "tot_evlu_amt": "2106055",
            "nass_amt": "2106055",
            "fncg_gld_auto_rdpt_yn": "",
            "pchs_amt_smtl_amt": "2516522",
            "evlu_amt_smtl_amt": "1759600",
            "evlu_pfls_smtl_amt": "-756922",
            "tot_stln_slng_chgs": "0",
            "bfdy_tot_asst_evlu_amt": "2142945",
            "asst_icdc_amt": "-36890",
            "asst_icdc_erng_rt": "0.00000000"
        }
    ],
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 주식일별주문체결조회

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `v1_국내주식-005` |
| 실전 TR_ID | `(3개월이내) TTTC0081R (3개월이전) CTSC9215R` |
| 모의 TR_ID | `(3개월이내) VTTC0081R (3개월이전) VTSC9215R` |
| HTTP Method | `GET` |
| URL 명 | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

주식일별주문체결조회 API입니다. 
실전계좌의 경우, 한 번의 호출에 최대 100건까지 확인 가능하며, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 
모의계좌의 경우, 한 번의 호출에 최대 15건까지 확인 가능하며, 이후의 값은 연속조회를 통해 확인하실 수 있습니다. 

* 다만, 3개월 이전 체결내역 조회(CTSC9115R) 의 경우, 
장중에는 많은 거래량으로 인해 순간적으로 DB가 밀렸거나 응답을 늦게 받거나 하는 등의 이슈가 있을 수 있어
① 가급적 장 종료 이후(15:30 이후) 조회하시고 
② 조회기간(INQR_STRT_DT와 INQR_END_DT 사이의 간격)을 보다 짧게 해서 조회하는 것을
권유드립니다.

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  / 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  / 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| `tr_id` | 거래ID | string | Y | 13 | ※ 구TR은 사전고지 없이 막힐 수 있으므로 반드시 신TR로 변경이용 부탁드립니다. / [실전투자] / 3개월이내 (구)TTTC8001R → (신)TTTC0081R  / 3개월이전 (구)CTSC9115R → (신)CTSC9215R / [모의투자] / 3개월이내 (구)VTTC8001R → (신)VTTC0081R  / 3개월이전 (구)VTSC9115R → (신)VTSC9215R |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | 공백 : 초기 조회 / N : 다음 데이터 조회 (output header의 tr_cont가 M일 경우) |
| `custtype` | 고객 타입 | string | Y | 1 | B : 법인  / P : 개인 |
| `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
| `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  / ex) 01011112222 (하이픈 등 구분값 제거) |
| `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Request Query Parameter

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `CANO` | 종합계좌번호 | string | Y | 8 | 계좌번호 체계(8-2)의 앞 8자리 |
| `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 계좌번호 체계(8-2)의 뒤 2자리 |
| `INQR_STRT_DT` | 조회시작일자 | string | Y | 8 | YYYYMMDD |
| `INQR_END_DT` | 조회종료일자 | string | Y | 8 | YYYYMMDD |
| `SLL_BUY_DVSN_CD` | 매도매수구분코드 | string | Y | 2 | 00 : 전체 / 01 : 매도 / 02 : 매수 |
| `PDNO` | 상품번호 | string | N | 12 | 종목번호(6자리) |
| `ORD_GNO_BRNO` | 주문채번지점번호 | string | Y | 5 | 주문시 한국투자증권 시스템에서 지정된 영업점코드 |
| `ODNO` | 주문번호 | string | N | 10 | 주문시 한국투자증권 시스템에서 채번된 주문번호 |
| `CCLD_DVSN` | 체결구분 | string | Y | 2 | '00 전체 / 01 체결 / 02 미체결' |
| `INQR_DVSN` | 조회구분 | string | Y | 2 | '00 역순 / 01 정순' |
| `INQR_DVSN_1` | 조회구분1 | string | Y | 1 | '없음: 전체 / 1: ELW / 2: 프리보드' |
| `INQR_DVSN_3` | 조회구분3 | string | Y | 2 | '00 전체 / 01 현금 / 02 신용 / 03 담보 / 04 대주 / 05 대여 / 06 자기융자신규/상환 / 07 유통융자신규/상환' |
| `EXCG_ID_DVSN_CD` | 거래소ID구분코드 | string | Y | 3 | 한국거래소 : KRX / 대체거래소 (NXT) : NXT / SOR (Smart Order Routing) : SOR / ALL : 전체 / ※ 모의투자는 KRX만 제공 |
| `CTX_AREA_FK100` | 연속조회검색조건100 | string | Y | 100 | '공란 : 최초 조회시는  / 이전 조회 Output CTX_AREA_FK100 값 : 다음페이지 조회시(2번째부터)' |
| `CTX_AREA_NK100` | 연속조회키100 | string | Y | 100 | '공란 : 최초 조회시  / 이전 조회 Output CTX_AREA_NK100 값 : 다음페이지 조회시(2번째부터)' |

### Response Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `tr_id` | 거래ID | string | Y | 13 | 요청한 tr_id |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | F or M : 다음 데이터 있음 / D or E : 마지막 데이터 |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
| `msg_cd` | 응답코드 | string | Y | 8 |  |
| `msg1` | 응답메세지 | string | Y | 80 |  |
| `output1` | 응답상세 | object array | Y |  | array |
| `ord_dt` | 주문일자 | string | Y | 8 |  |
| `ord_gno_brno` | 주문채번지점번호 | string | Y | 5 |  |
| `odno` | 주문번호 | string | Y | 10 |  |
| `orgn_odno` | 원주문번호 | string | Y | 10 |  |
| `ord_dvsn_name` | 주문구분명 | string | Y | 60 |  |
| `sll_buy_dvsn_cd` | 매도매수구분코드 | string | Y | 2 |  |
| `sll_buy_dvsn_cd_name` | 매도매수구분코드명 | string | Y | 60 |  |
| `pdno` | 상품번호 | string | Y | 12 |  |
| `prdt_name` | 상품명 | string | Y | 60 |  |
| `ord_qty` | 주문수량 | string | Y | 10 |  |
| `ord_unpr` | 주문단가 | string | Y | 19 |  |
| `ord_tmd` | 주문시각 | string | Y | 6 |  |
| `tot_ccld_qty` | 총체결수량 | string | Y | 10 |  |
| `avg_prvs` | 평균가 | string | Y | 19 |  |
| `cncl_yn` | 취소여부 | string | Y | 1 |  |
| `tot_ccld_amt` | 총체결금액 | string | Y | 19 |  |
| `loan_dt` | 대출일자 | string | Y | 8 |  |
| `ordr_empno` | 주문자사번 | string | Y | 60 |  |
| `ord_dvsn_cd` | 주문구분코드 | string | Y | 2 |  |
| `cnc_cfrm_qty` | 취소확인수량 | string | Y | 10 |  |
| `rmn_qty` | 잔여수량 | string | Y | 10 |  |
| `rjct_qty` | 거부수량 | string | Y | 10 |  |
| `ccld_cndt_name` | 체결조건명 | string | Y | 10 |  |
| `inqr_ip_addr` | 조회IP주소 | string | Y | 15 |  |
| `cpbc_ordp_ord_rcit_dvsn_cd` | 전산주문표주문접수구분코드 | string | Y | 2 |  |
| `cpbc_ordp_infm_mthd_dvsn_cd` | 전산주문표통보방법구분코드 | string | Y | 2 |  |
| `infm_tmd` | 통보시각 | string | Y | 6 |  |
| `ctac_tlno` | 연락전화번호 | string | Y | 20 |  |
| `prdt_type_cd` | 상품유형코드 | string | Y | 3 |  |
| `excg_dvsn_cd` | 거래소구분코드 | string | Y | 2 |  |
| `cpbc_ordp_mtrl_dvsn_cd` | 전산주문표자료구분코드 | string | Y | 2 |  |
| `ord_orgno` | 주문조직번호 | string | Y | 5 |  |
| `rsvn_ord_end_dt` | 예약주문종료일자 | string | Y | 8 |  |
| `excg_id_dvsn_Cd` | 거래소ID구분코드 | string | Y | 3 |  |
| `stpm_cndt_pric` | 스톱지정가조건가격 | string | Y | 9 |  |
| `stpm_efct_occr_dtmd` | 스톱지정가효력발생상세시각 | string | Y | 9 |  |
| `output2` | 응답상세 | object | Y |  | single |
| `tot_ord_qty` | 총주문수량 | string | Y | 10 |  |
| `tot_ccld_qty` | 총체결수량 | string | Y | 10 |  |
| `tot_ccld_amt` | 매입평균가격 | string | Y | 19 |  |
| `prsm_tlex_smtl` | 총체결금액 | string | Y | 19 |  |
| `pchs_avg_pric` | 추정제비용합계 | string | Y | 184 |  |

### Request 예시

```json
{
	"CANO": "12345678",
	"ACNT_PRDT_CD": "01",
	"INQR_STRT_DT": "20211101",
	"INQR_END_DT": "20211101",
	"SLL_BUY_DVSN_CD": "00",
	"INQR_DVSN": "00",
	"PDNO": "",
	"CCLD_DVSN": "00",
	"ORD_GNO_BRNO": "",
	"ODNO": "",
	"INQR_DVSN_3": "00",
	"INQR_DVSN_1": "",
	"CTX_AREA_FK100": "",
	"CTX_AREA_NK100": ""
}
```

### Response 예시

```json
{
  "ctx_area_fk100": "12345678^01^20220103^20220103^ ^00^00^                                                              ",
  "ctx_area_nk100": "                                                                                                    ",
  "output1": [
    {
      "ord_dt": "20220103",
      "ord_gno_brno": "06010",
      "odno": "0001568197",
      "orgn_odno": "",
      "ord_dvsn_name": "Limit",
      "sll_buy_dvsn_cd": "02",
      "sll_buy_dvsn_cd_name": "BUY REJECT",
      "pdno": "009150",
      "prdt_name": "삼성전기",
      "ord_qty": "10",
      "ord_unpr": "150000",
      "ord_tmd": "170100",
      "tot_ccld_qty": "0",
      "avg_prvs": "0",
      "cncl_yn": "",
      "tot_ccld_amt": "0",
      "loan_dt": "",
      "ordr_empno": "Nsmart",
      "ord_dvsn_cd": "00",
      "cncl_cfrm_qty": "0",
      "rmn_qty": "0",
      "rjct_qty": "10",
      "ccld_cndt_name": "None",
      "inqr_ip_addr": "...",
      "cpbc_ordp_ord_rcit_dvsn_cd": "",
      "cpbc_ordp_infm_mthd_dvsn_cd": "",
      "infm_tmd": "",
      "ctac_tlno": "01047859775",
      "prdt_type_cd": "300",
      "excg_dvsn_cd": "02",
      "cpbc_ordp_mtrl_dvsn_cd": "11",
      "ord_orgno": "00000",
      "rsvn_ord_end_dt": ""
    },
    {
      "ord_dt": "20220103",
      "ord_gno_brno": "06010",
      "odno": "0001568196",
      "orgn_odno": "",
      "ord_dvsn_name": "Limit",
      "sll_buy_dvsn_cd": "02",
      "sll_buy_dvsn_cd_name": "BUY REJECT",
      "pdno": "009150",
      "prdt_name": "삼성전기",
      "ord_qty": "10",
      "ord_unpr": "150000",
      "ord_tmd": "170038",
      "tot_ccld_qty": "0",
      "avg_prvs": "0",
      "cncl_yn": "",
      "tot_ccld_amt": "0",
      "loan_dt": "",
      "ordr_empno": "Nsmart",
      "ord_dvsn_cd": "00",
      "cncl_cfrm_qty": "0",
      "rmn_qty": "0",
      "rjct_qty": "10",
      "ccld_cndt_name": "None",
      "inqr_ip_addr": "P01.012.345.678",
      "cpbc_ordp_ord_rcit_dvsn_cd": "",
      "cpbc_ordp_infm_mthd_dvsn_cd": "",
      "infm_tmd": "",
      "ctac_tlno": "01047859775",
      "prdt_type_cd": "300",
      "excg_dvsn_cd": "02",
      "cpbc_ordp_mtrl_dvsn_cd": "11",
      "ord_orgno": "00000",
      "rsvn_ord_end_dt": ""
	}
		],
  "output2": {
    "tot_ord_qty": "281",
    "tot_ccld_qty": "0",
    "tot_ccld_amt": "0",
    "prsm_tlex_smtl": "0",
    "pchs_avg_pric": "0.0000"
  },
  "rt_cd": "0",
  "msg_cd": "KIOK0510",
  "msg1": "조회가 완료되었습니다                                                           "
}
```

---

## 접근토큰발급(P)

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `인증-001` |
| HTTP Method | `POST` |
| URL 명 | `/oauth2/tokenP` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

본인 계좌에 필요한 인증 절차로, 인증을 통해 접근 토큰을 부여받아 오픈API 활용이 가능합니다.

1. 접근토큰(access_token)의 유효기간은 24시간 이며(1일 1회발급 원칙) 
   갱신발급주기는 6시간 입니다.(6시간 이내는 기존 발급키로 응답)

2. 접근토큰발급(/oauth2/tokenP) 시 접근토큰값(access_token)과 함께 수신되는 
   접근토큰 유효기간(acess_token_token_expired)을 이용해 접근토큰을 관리하실 수 있습니다.


[참고]

'23.4.28 이후 지나치게 잦은 토큰 발급 요청건을 제어 하기 위해 신규 접근토큰발급 이후 일정시간 이내에 재호출 시에는 직전 토큰값을 리턴하게 되었습니다. 일정시간 이후 접근토큰발급 API 호출 시에는 신규 토큰값을 리턴합니다. 
접근토큰발급 API 호출 및 코드 작성하실 때 해당 사항을 참고하시길 바랍니다.

※ 참고 : 포럼 &gt; 공지사항 &gt;  [수정] [중요] 접근 토큰 발급 변경 안내

### Request Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `grant_type` | 권한부여 Type | string | Y | 18 | client_credentials |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appsecret (절대 노출되지 않도록 주의해주세요.) |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `access_token` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token / ex) "eyJ0eXUxMiJ9.eyJz…..................................." /  /  - 일반개인고객/일반법인고객 /   . Access token 유효기간 1일 /   .. 일정시간(6시간) 이내에 재호출 시에는 직전 토큰값을 리턴 /   . OAuth 2.0의 Client Credentials Grant 절차를 준용 /  /  - 제휴법인 /   . Access token 유효기간 3개월 /   . Refresh token 유효기간 1년 /   . OAuth 2.0의 Authorization Code Grant 절차를 준용 |
| `token_type` | 접근토큰유형 | string | Y | 20 | 접근토큰유형 : "Bearer" / ※ API 호출 시, 접근토큰유형 "Bearer" 입력. ex) "Bearer eyJ...." |
| `expires_in` | 접근토큰 유효기간 | number | Y | 10 | 유효기간(초) / ex) 7776000 |
| `access_token_token_expired` | 접근토큰 유효기간(일시표시) | string | Y | 50 | 유효기간(년:월:일 시:분:초) / ex) "2022-08-30 08:10:10" |

### Request 예시

```json
{
  "grant_type": "client_credentials",
  "appkey": "PSg5dctL9dKPo727J13Ur405OSXXXXXXXXXX",
  "appsecret":  "yo2t8zS68zpdjGuWvFyM9VikjXE0i0CbgPEamnqPA00G0bIfrdfQb2RUD1xP7SqatQXr1cD1fGUNsb78MMXoq6o4lAYt9YTtHAjbMoFy+c72kbq5owQY1Pvp39/x6ejpJlXCj7gE3yVOB/h25Hvl+URmYeBTfrQeOqIAOYc/OIXXXXXXXXXX"
}
```

### Response 예시

```json
{
	"access_token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0b2tlbiIsImF1ZCI6ImMwNzM1NTYzLTA1MjctNDNhZS05ODRiLTJiNWI1ZWZmOWYyMyIsImlzcyI6InVub2d3IiwiZXhwIjoxNjQ5NzUxMTAwLCJpYXQiOjE2NDE5NzUxMDAsImp0aSI6IkJTZlM0QUtSSnpRVGpmdHRtdXZlenVQUTlKajc3cHZGdjBZVyJ9.Oyt_C639yUjWmRhymlszgt6jDo8fvIKkkxH1mMngunV1T15SCC4I3Xe6MXxcY23DXunzBfR1uI0KXXXXXXXXXX",
	"access_token_token_expired":"2023-12-22 08:16:59",
	"token_type":"Bearer",
	"expires_in":86400
}
```

---

## 주식주문(현금)

### 기본 정보

| 항목 | 값 |
|------|-----|
| API ID | `v1_국내주식-001` |
| 실전 TR_ID | `(매도) TTTC0011U (매수) TTTC0012U` |
| 모의 TR_ID | `(매도) VTTC0011U (매수) VTTC0012U` |
| HTTP Method | `POST` |
| URL 명 | `/uapi/domestic-stock/v1/trading/order-cash` |
| 실전 Domain | `https://openapi.koreainvestment.com:9443` |
| 모의 Domain | `https://openapivts.koreainvestment.com:29443` |

### 개요

국내주식주문(현금) API 입니다. 

※ TTC0802U(현금매수) 사용하셔서 미수매수 가능합니다. 단, 거래하시는 계좌가 증거금40%계좌로 신청이 되어있어야 가능합니다. 
※ 신용매수는 별도의 API가 준비되어 있습니다.

※ ORD_QTY(주문수량), ORD_UNPR(주문단가) 등을 String으로 전달해야 함에 유의 부탁드립니다.

※ ORD_UNPR(주문단가)가 없는 주문은 상한가로 주문금액을 선정하고 이후 체결이되면 체결금액로 정산됩니다.

※ POST API의 경우 BODY값의 key값들을 대문자로 작성하셔야 합니다.
   (EX. "CANO" : "12345678", "ACNT_PRDT_CD": "01",...)

※ 종목코드 마스터파일 파이썬 정제코드는 한국투자증권 Github 참고 부탁드립니다.
   https://github.com/koreainvestment/open-trading-api/tree/main/stocks_info

### Request Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |
| `authorization` | 접근토큰 | string | Y | 350 | OAuth 토큰이 필요한 API 경우 발급한 Access token  / 일반고객(Access token 유효기간 1일, OAuth 2.0의 Client Credentials Grant 절차를 준용)  / 법인(Access token 유효기간 3개월, Refresh token 유효기간 1년, OAuth 2.0의 Authorization Code Grant 절차를 준용) /  / ※ 토큰 지정시 토큰 타입("Bearer") 지정 필요. 즉, 발급받은 접근토큰 앞에 앞에 "Bearer" 붙여서 호출 / EX) "Bearer eyJ..........8GA" |
| `appkey` | 앱키 | string | Y | 36 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `appsecret` | 앱시크릿키 | string | Y | 180 | 한국투자증권 홈페이지에서 발급받은 appkey (절대 노출되지 않도록 주의해주세요.) |
| `personalseckey` | 고객식별키 | string | N | 180 | [법인 필수] 제휴사 회원 관리를 위한 고객식별키 |
| `tr_id` | 거래ID | string | Y | 13 | '※ 구TR은 사전고지 없이 막힐 수 있으므로 반드시 신TR로 변경이용 부탁드립니다. / [실전투자] / 국내주식주문 매도 : (구)TTTC0801U → (신)TTTC0011U / 국내주식주문 매도(모의투자) : (구)VTTC0801U → (신)VTTC0011U / 국내주식주문 매수 : (구)TTTC0802U → (신)TTTC0012U / 국내주식주문 매수(모의투자) : (구)VTTC0802U → (신)VTTC0012U' |
| `tr_cont` | 연속 거래 여부 | string | N | 1 | tr_cont를 이용한 다음조회 불가 API |
| `custtype` | 고객 타입 | string | Y | 1 | B : 법인  / P : 개인 |
| `seq_no` | 일련번호 | string | N | 2 | [법인 필수] 001 |
| `mac_address` | 맥주소 | string | N | 12 | 법인고객 혹은 개인고객의 Mac address 값 |
| `phone_number` | 핸드폰번호 | string | N | 12 | [법인 필수] 제휴사APP을 사용하는 경우 사용자(회원) 핸드폰번호  / ex) 01011112222 (하이픈 등 구분값 제거) |
| `ip_addr` | 접속 단말 공인 IP | string | N | 12 | [법인 필수] 사용자(회원)의 IP Address |
| `gt_uid` | Global UID | string | N | 32 | [법인 전용] 거래고유번호로 사용하므로 거래별로 UNIQUE해야 함 |

### Request Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `CANO` | 종합계좌번호 | string | Y | 8 | 종합계좌번호 |
| `ACNT_PRDT_CD` | 계좌상품코드 | string | Y | 2 | 상품유형코드 |
| `PDNO` | 상품번호 | string | Y | 12 | 종목코드(6자리) , ETN의 경우 7자리 입력 |
| `SLL_TYPE` | 매도유형 (매도주문 시) | string | N | 2 | 01@일반매도 / 02@임의매매 / 05@대차매도 / → 미입력시 01 일반매도로 진행 |
| `ORD_DVSN` | 주문구분 | string | Y | 2 | [KRX] / 00 : 지정가 / 01 : 시장가 / 02 : 조건부지정가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 05 : 장전 시간외 / 06 : 장후 시간외 / 07 : 시간외 단일가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) / 21 : 중간가 / 22 : 스톱지정가 / 23 : 중간가IOC / 24 : 중간가FOK /  / [NXT] / 00 : 지정가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) / 21 : 중간가 / 22 : 스톱지정가 / 23 : 중간가IOC / 24 : 중간가FOK /  / [SOR] / 00 : 지정가 / 01 : 시장가 / 03 : 최유리지정가 / 04 : 최우선지정가 / 11 : IOC지정가 (즉시체결,잔량취소) / 12 : FOK지정가 (즉시체결,전량취소) / 13 : IOC시장가 (즉시체결,잔량취소) / 14 : FOK시장가 (즉시체결,전량취소) / 15 : IOC최유리 (즉시체결,잔량취소) / 16 : FOK최유리 (즉시체결,전량취소) |
| `ORD_QTY` | 주문수량 | string | Y | 10 | 주문수량 |
| `ORD_UNPR` | 주문단가 | string | Y | 19 | 주문단가 / 시장가 등 주문시, "0"으로 입력 |
| `CNDT_PRIC` | 조건가격 | string | N | 19 | 스탑지정가호가 주문 (ORD_DVSN이 22) 사용 시에만 필수 |
| `EXCG_ID_DVSN_CD` | 거래소ID구분코드 | string | N | 3 | 한국거래소 : KRX / 대체거래소 (넥스트레이드) : NXT / SOR (Smart Order Routing) : SOR / → 미입력시 KRX로 진행되며, 모의투자는 KRX만 가능 |

### Response Header

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `content-type` | 컨텐츠타입 | string | Y | 40 | application/json; charset=utf-8 |

### Response Body

| Element | 한글명 | Type | Required | Length | Description |
|---------|--------|------|----------|--------|-------------|
| `rt_cd` | 성공 실패 여부 | string | Y | 1 |  |
| `msg_cd` | 응답코드 | string | Y | 8 |  |
| `msg1` | 응답메세지 | string | Y | 80 |  |
| `output` | 응답상세 | object array | Y |  | single |
| `KRX_FWDG_ORD_ORGNO` | 계좌관리점코드 | string | Y | 5 |  |
| `ODNO` | 주문번호 | string | Y | 10 |  |
| `ORD_TMD` | 주문시간 | string | Y | 6 |  |

### Request 예시

```json
{
	"CANO": "810XXXXX",
	"ACNT_PRDT_CD": "01",
	"PDNO": "009150",
	"ORD_DVSN": "00",
	"ORD_QTY": "3",
	"ORD_UNPR": "150000"
}
```

### Response 예시

```json
{
  "rt_cd": "0",
  "msg_cd": "APBK0013",
  "msg1": "주문 전송 완료 되었습니다.",
  "output": {
    "KRX_FWDG_ORD_ORGNO": "06010",
    "ODNO": "0001569157",
    "ORD_TMD": "155211"
  }
}
```

---
