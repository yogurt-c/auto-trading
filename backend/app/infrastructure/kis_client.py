"""KIS (Korea Investment & Securities) Open API wrapper.

국내 주식 및 해외(미국) 주식 주문·조회를 단일 인터페이스로 제공합니다.

종목 구분 규칙:
  한국 주식: ticker가 6자리 숫자 (예: 005930, 035720)
  미국 주식: 영문 티커 (예: AAPL, TSLA)

API 도메인:
  실전: https://openapi.koreainvestment.com:9443
  모의: https://openapivts.koreainvestment.com:29443
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from loguru import logger

from .config import get_settings

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

_REAL_BASE = "https://openapi.koreainvestment.com:9443"
_PAPER_BASE = "https://openapivts.koreainvestment.com:29443"

_KST = ZoneInfo("Asia/Seoul")

# 국내 TR_ID
_KR_BUY_REAL = "TTTC0012U"
_KR_SELL_REAL = "TTTC0011U"
_KR_BUY_PAPER = "VTTC0012U"
_KR_SELL_PAPER = "VTTC0011U"
_KR_BALANCE_REAL = "TTTC8434R"
_KR_BALANCE_PAPER = "VTTC8434R"
_KR_ORDER_INQUIRE_REAL = "TTTC0081R"
_KR_ORDER_INQUIRE_PAPER = "VTTC0081R"

# 해외(미국) TR_ID
_US_BUY_REAL = "TTTT1002U"
_US_SELL_REAL = "TTTT1006U"
_US_BUY_PAPER = "VTTT1002U"
_US_SELL_PAPER = "VTTT1001U"
_US_BALANCE_REAL = "TTTS3012R"
_US_BALANCE_PAPER = "VTTS3012R"
_US_ORDER_INQUIRE_REAL = "TTTS3035R"
_US_ORDER_INQUIRE_PAPER = "VTTS3035R"

# 현재가 조회 TR_ID
_KR_PRICE_INQUIRY = "FHKST01010100"

# 일별 주문체결조회 TR_ID
_KR_DAILY_CCLD_REAL = "TTTC8001R"
_KR_DAILY_CCLD_PAPER = "VTTC8001R"

# 주문 취소 TR_ID
_KR_CANCEL_REAL = "TTTC0013U"
_KR_CANCEL_PAPER = "VTTC0013U"
_US_CANCEL_REAL = "TTTT1004U"
_US_CANCEL_PAPER = "VTTT1004U"

# 기본 미국 거래소 (NASD=NASDAQ, NYSE, AMEX)
_DEFAULT_US_EXCHANGE = "NASD"

# ---------------------------------------------------------------------------
# 토큰 캐시 (24시간 유효, 만료 10분 전 자동 갱신)
# ---------------------------------------------------------------------------

_token_cache: dict = {"access_token": None, "expires_at": None}
_token_lock = threading.Lock()

# KIS client 재연결용 락
_reset_lock = threading.Lock()


def reset_client() -> None:
    """설정 변경 후 토큰 캐시를 초기화합니다."""
    with _token_lock:
        _token_cache["access_token"] = None
        _token_cache["expires_at"] = None
    logger.info("KIS token cache cleared")


def _base_url() -> str:
    return _PAPER_BASE if get_settings().kis_paper else _REAL_BASE


def _parse_account(account_no: str) -> tuple[str, str]:
    """계좌번호 파싱. '12345678' 또는 '12345678-01' 형식 모두 허용.
    상품코드(뒤 2자리) 생략 시 '01'로 기본 처리.
    """
    parts = account_no.split("-")
    if len(parts) == 2:
        return parts[0], parts[1]
    if len(parts) == 1 and parts[0]:
        return parts[0], "01"
    raise ValueError(f"계좌번호 형식이 잘못되었습니다: '{account_no}'. 8자리 숫자로 입력해 주세요.")


def _get_access_token() -> str:
    """유효한 Access Token 반환. 만료 10분 전이면 자동 갱신."""
    with _token_lock:
        now = datetime.now(_KST)
        expires_at = _token_cache.get("expires_at")
        token = _token_cache.get("access_token")

        if token and expires_at and expires_at > now + timedelta(minutes=10):
            return token

        # 신규 발급
        s = get_settings()
        if not s.kis_app_key or not s.kis_app_secret:
            raise ValueError("KIS API 키가 설정되지 않았습니다. Settings 페이지에서 입력해 주세요.")

        resp = httpx.post(
            f"{_base_url()}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": s.kis_app_key,
                "appsecret": s.kis_app_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if "access_token" not in data:
            raise RuntimeError(f"KIS 토큰 발급 실패: {data}")

        _token_cache["access_token"] = data["access_token"]
        # expires_in: 초 단위 (통상 86400 = 24시간)
        expires_in = int(data.get("expires_in", 86400))
        _token_cache["expires_at"] = now + timedelta(seconds=expires_in)

        logger.info(f"KIS access token issued, expires in {expires_in}s")
        return _token_cache["access_token"]


def _headers(tr_id: str) -> dict:
    """공통 요청 헤더."""
    s = get_settings()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_access_token()}",
        "appkey": s.kis_app_key,
        "appsecret": s.kis_app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }


def _check_response(data: dict, context: str = "") -> dict:
    """rt_cd != '0' 이면 RuntimeError 발생."""
    rt_cd = data.get("rt_cd", "")
    if rt_cd != "0":
        msg = data.get("msg1", data.get("msg_cd", "unknown error"))
        raise RuntimeError(f"KIS API 오류{f' ({context})' if context else ''}: [{rt_cd}] {msg}")
    return data


# ---------------------------------------------------------------------------
# 종목 구분 유틸
# ---------------------------------------------------------------------------


def is_korean_ticker(ticker: str) -> bool:
    """6자리 숫자이면 국내 주식, 아니면 해외(미국) 주식."""
    return ticker.isdigit() and len(ticker) == 6


def ticker_market(ticker: str) -> str:
    """'KR' 또는 'US' 반환."""
    return "KR" if is_korean_ticker(ticker) else "US"


def ticker_currency(ticker: str) -> str:
    """'KRW' 또는 'USD' 반환."""
    return "KRW" if is_korean_ticker(ticker) else "USD"


# ---------------------------------------------------------------------------
# 계좌 조회
# ---------------------------------------------------------------------------


def get_account() -> dict:
    """KIS 계좌 잔고 요약 반환. 국내(KRW) + 해외(USD) 분리."""
    s = get_settings()
    if not s.kis_account_no:
        raise ValueError("KIS 계좌번호가 설정되지 않았습니다.")

    kr = _get_domestic_balance()

    try:
        us = _get_overseas_balance_summary()
    except Exception as e:
        logger.warning(f"해외 계좌 잔고 조회 실패 (0으로 처리): {e}")
        us = {"us_cash": 0.0, "us_buying_power": 0.0, "us_portfolio_value": 0.0}

    return {
        **kr,
        **us,
        "status": "normal",
        "is_paper": s.kis_paper,
    }


def _get_domestic_balance() -> dict:
    """국내 계좌 잔고 요약 (KRW)."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)
    tr_id = _KR_BALANCE_PAPER if s.kis_paper else _KR_BALANCE_REAL

    resp = httpx.get(
        f"{_base_url()}/uapi/domestic-stock/v1/trading/inquire-balance",
        headers=_headers(tr_id),
        params={
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = _check_response(resp.json(), "domestic-balance-summary")

    raw = data.get("output2", [{}])
    summary = raw[0] if isinstance(raw, list) and raw else (raw if isinstance(raw, dict) else {})

    return {
        "kr_cash": float(summary.get("dnca_tot_amt", 0)),
        "kr_portfolio_value": float(summary.get("tot_evlu_amt", 0)),
        "kr_buying_power": float(summary.get("nass_amt", 0)),
    }


def _get_overseas_balance_summary() -> dict:
    """해외(미국) 계좌 잔고 요약 (USD). 5xx 오류 시 최대 3회 재시도."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)
    tr_id = _US_BALANCE_PAPER if s.kis_paper else _US_BALANCE_REAL

    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            delay = attempt
            logger.info(f"해외 잔고 요약 재시도 {attempt}/2 ({delay}s 대기)")
            time.sleep(delay)
        resp = httpx.get(
            f"{_base_url()}/uapi/overseas-stock/v1/trading/inquire-balance",
            headers=_headers(tr_id),
            params={
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "OVRS_EXCG_CD": _DEFAULT_US_EXCHANGE,
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            },
            timeout=10,
        )
        if resp.status_code >= 500:
            try:
                err_body = resp.json()
                logger.error(
                    f"해외 잔고 요약 조회 HTTP {resp.status_code}: "
                    f"rt_cd={err_body.get('rt_cd')} msg={err_body.get('msg1', '').strip()}"
                )
            except Exception:
                logger.error(f"해외 잔고 요약 조회 HTTP {resp.status_code}: {resp.text[:200]}")
            last_exc = RuntimeError(f"HTTP {resp.status_code}")
            continue
        resp.raise_for_status()
        break
    else:
        raise last_exc  # type: ignore[misc]

    data = _check_response(resp.json(), "overseas-balance-summary")

    raw = data.get("output2", {})
    summary = raw[0] if isinstance(raw, list) and raw else raw if isinstance(raw, dict) else {}

    # 포지션 합산으로 총 평가금액 계산 (ovrs_stck_evlu_amt: 검증된 필드명)
    positions = data.get("output1", [])
    us_portfolio_value = sum(
        float(item.get("ovrs_stck_evlu_amt", 0))
        for item in positions
        if float(item.get("ovrs_cblc_qty", 0)) > 0
    )

    # frcr_dncl_amt_2: 외화예수금, frcr_ord_psbl_amt1: 외화주문가능금액
    return {
        "us_cash": float(summary.get("frcr_dncl_amt_2", 0)),
        "us_buying_power": float(summary.get("frcr_ord_psbl_amt1", 0)),
        "us_portfolio_value": us_portfolio_value,
    }


# ---------------------------------------------------------------------------
# 포지션 조회
# ---------------------------------------------------------------------------


def _get_domestic_positions() -> list[dict]:
    """국내 보유 종목 조회. 5xx 오류 시 최대 3회 재시도."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)
    tr_id = _KR_BALANCE_PAPER if s.kis_paper else _KR_BALANCE_REAL

    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            delay = attempt  # 1s, 2s
            logger.info(f"국내 포지션 재시도 {attempt}/2 ({delay}s 대기)")
            time.sleep(delay)
        resp = httpx.get(
            f"{_base_url()}/uapi/domestic-stock/v1/trading/inquire-balance",
            headers=_headers(tr_id),
            params={
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "01",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "01",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
            timeout=10,
        )
        if resp.status_code >= 500:
            try:
                err_body = resp.json()
                logger.error(
                    f"국내 포지션 조회 HTTP {resp.status_code}: "
                    f"rt_cd={err_body.get('rt_cd')} msg_cd={err_body.get('msg_cd')} "
                    f"msg={err_body.get('msg1', '').strip()}"
                )
            except Exception:
                logger.error(f"국내 포지션 조회 HTTP {resp.status_code}: {resp.text[:200]}")
            last_exc = RuntimeError(f"HTTP {resp.status_code}")
            continue
        resp.raise_for_status()  # 4xx: 즉시 전파 (재시도 안 함)
        break
    else:
        raise last_exc  # type: ignore[misc]

    data = _check_response(resp.json(), "domestic-balance")

    result = []
    for item in data.get("output1", []):
        qty = float(item.get("hldg_qty", 0))
        if qty <= 0:
            continue
        result.append(
            {
                "ticker": item.get("pdno", ""),
                "qty": qty,
                "avg_entry_price": float(item.get("pchs_avg_pric", 0)),
                "current_price": float(item.get("prpr", 0)),
                "market_value": float(item.get("evlu_amt", 0)),
                "unrealized_pl": float(item.get("evlu_pfls_amt", 0)),
                "unrealized_plpc": float(item.get("evlu_pfls_rt", 0)),
                "market": "KR",
                "currency": "KRW",
            }
        )
    return result


def _get_overseas_positions() -> list[dict]:
    """해외(미국) 보유 종목 조회. 5xx 오류 시 최대 3회 재시도."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)
    tr_id = _US_BALANCE_PAPER if s.kis_paper else _US_BALANCE_REAL

    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt > 0:
            delay = attempt  # 1s, 2s
            logger.info(f"해외 포지션 재시도 {attempt}/2 ({delay}s 대기)")
            time.sleep(delay)
        resp = httpx.get(
            f"{_base_url()}/uapi/overseas-stock/v1/trading/inquire-balance",
            headers=_headers(tr_id),
            params={
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "OVRS_EXCG_CD": _DEFAULT_US_EXCHANGE,
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": "",
            },
            timeout=10,
        )
        if resp.status_code >= 500:
            # 응답 바디에 KIS 오류 메시지가 있을 수 있으므로 로깅
            try:
                err_body = resp.json()
                logger.error(
                    f"해외 포지션 조회 HTTP {resp.status_code}: "
                    f"rt_cd={err_body.get('rt_cd')} msg_cd={err_body.get('msg_cd')} "
                    f"msg={err_body.get('msg1', '').strip()}"
                )
            except Exception:
                logger.error(f"해외 포지션 조회 HTTP {resp.status_code}: {resp.text[:200]}")
            last_exc = RuntimeError(f"HTTP {resp.status_code}")
            continue
        resp.raise_for_status()  # 4xx: 즉시 전파 (재시도 안 함)
        break
    else:
        raise last_exc  # type: ignore[misc]

    data = _check_response(resp.json(), "overseas-balance")

    result = []
    for item in data.get("output1", []):
        # 스펙 필드명: ovrs_cblc_qty(잔고수량), ovrs_pdno(종목코드),
        #              ovrs_stck_evlu_amt(평가금액), frcr_evlu_pfls_amt(외화평가손익)
        qty = float(item.get("ovrs_cblc_qty", 0))
        if qty <= 0:
            continue
        result.append(
            {
                "ticker": item.get("ovrs_pdno", ""),
                "qty": qty,
                "avg_entry_price": float(item.get("pchs_avg_pric", 0)),
                "current_price": float(item.get("now_pric2", 0)),
                "market_value": float(item.get("ovrs_stck_evlu_amt", 0)),
                "unrealized_pl": float(item.get("frcr_evlu_pfls_amt", 0)),
                "unrealized_plpc": float(item.get("evlu_pfls_rt", 0)),
                "market": "US",
                "currency": "USD",
            }
        )
    return result


def get_positions() -> list[dict]:
    """국내 + 해외 전체 보유 포지션 반환."""
    domestic = _get_domestic_positions()
    try:
        overseas = _get_overseas_positions()
    except Exception as e:
        logger.warning(f"해외 포지션 조회 실패 (무시하고 계속): {e}")
        overseas = []
    return domestic + overseas


# ---------------------------------------------------------------------------
# 주문 단건 조회
# ---------------------------------------------------------------------------


def get_order(broker_order_id: str, market: str = "US") -> dict:
    """브로커 주문번호로 주문 상태 조회.

    market: 'KR' 또는 'US'
    """
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)

    if market == "KR":
        today = datetime.now(tz=_KST).strftime("%Y%m%d")
        tr_id = _KR_ORDER_INQUIRE_PAPER if s.kis_paper else _KR_ORDER_INQUIRE_REAL
        resp = httpx.get(
            f"{_base_url()}/uapi/domestic-stock/v1/trading/inquire-order",
            headers=_headers(tr_id),
            params={
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "ODNO": broker_order_id,
                "ORD_GNO_BRNO": "",
                "INQR_DVSN": "01",
                "INQR_STRT_DT": today,
                "INQR_END_DT": today,
            },
            timeout=10,
        )
    else:
        tr_id = _US_ORDER_INQUIRE_PAPER if s.kis_paper else _US_ORDER_INQUIRE_REAL
        resp = httpx.get(
            f"{_base_url()}/uapi/overseas-stock/v1/trading/inquire-order",
            headers=_headers(tr_id),
            params={
                "CANO": cano,
                "ACNT_PRDT_CD": acnt_cd,
                "OVRS_EXCG_CD": _DEFAULT_US_EXCHANGE,
                "ODNO": broker_order_id,
                "INQR_DVSN": "00",
            },
            timeout=10,
        )

    resp.raise_for_status()
    data = _check_response(resp.json(), f"inquire-order ({market})")

    output = data.get("output", {})
    if isinstance(output, list):
        output = output[0] if output else {}

    # KIS 체결 상태 → 내부 status 매핑
    status_raw = output.get("ord_stts", output.get("odno_stts", ""))
    status = _map_order_status(status_raw)

    filled_qty = float(output.get("tot_ccld_qty", output.get("ccld_qty", 0)) or 0)
    filled_price = float(output.get("avg_prvs", output.get("ccld_unpr", 0)) or 0) or None

    return {
        "broker_order_id": broker_order_id,
        "status": status,
        "filled_avg_price": filled_price if filled_price else None,
        "filled_qty": filled_qty if filled_qty else None,
    }


def _map_order_status(raw: str) -> str:
    """KIS 주문 상태 코드 → 내부 상태 문자열 변환."""
    mapping = {
        "02": "filled",  # 체결
        "01": "partially_filled",  # 부분체결
        "00": "pending",  # 접수
        "03": "canceled",  # 취소
        "04": "rejected",  # 거부
    }
    return mapping.get(raw, "pending")


# ---------------------------------------------------------------------------
# 체결 이력 조회
# ---------------------------------------------------------------------------


def get_filled_orders(limit: int = 50) -> list[dict]:
    """최근 체결 완료된 주문 이력 반환 (국내 기준)."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)
    tr_id = _KR_DAILY_CCLD_PAPER if s.kis_paper else _KR_DAILY_CCLD_REAL

    today = datetime.now(_KST).strftime("%Y%m%d")

    resp = httpx.get(
        f"{_base_url()}/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
        headers=_headers(tr_id),
        params={
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_cd,
            "INQR_STRT_DT": today,
            "INQR_END_DT": today,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "01",
            "PDNO": "",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "CCLD_DVSN": "01",
            "INQR_DVSN_1": "",
            "INQR_DVSN_3": "00",
            "EXCG_ID_DVSN_CD": "KRX",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = _check_response(resp.json(), "inquire-daily-ccld")

    result = []
    for item in data.get("output1", [])[:limit]:
        filled_qty = float(item.get("tot_ccld_qty", 0))
        filled_price = float(item.get("avg_prvs", 0))
        result.append(
            {
                "id": item.get("odno", ""),
                "ticker": item.get("pdno", ""),
                "action": "buy" if item.get("sll_buy_dvsn_cd") == "02" else "sell",
                "shares": filled_qty,
                "price": filled_price,
                "total": filled_qty * filled_price,
                "executed_at": item.get("ord_tmd", ""),
            }
        )
    return result


# ---------------------------------------------------------------------------
# 주문 실행
# ---------------------------------------------------------------------------


def place_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str = "market",
    limit_price: float | None = None,
) -> dict:
    """주문 실행 (국내/해외 자동 분기).

    Returns:
        broker_order_id, ticker, side, qty, order_type, status,
        limit_price, filled_avg_price, market, currency
    """
    if is_korean_ticker(ticker):
        return _place_domestic_order(ticker, side, qty, order_type, limit_price)
    else:
        return _place_overseas_order(ticker, side, qty, order_type, limit_price)


def _place_domestic_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str,
    limit_price: float | None,
) -> dict:
    """국내 주식 주문."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)

    is_buy = side.lower() == "buy"
    if is_buy:
        tr_id = _KR_BUY_PAPER if s.kis_paper else _KR_BUY_REAL
    else:
        tr_id = _KR_SELL_PAPER if s.kis_paper else _KR_SELL_REAL

    # 국내: 시장가=01, 지정가=00
    ord_dvsn = "00" if order_type == "limit" and limit_price else "01"
    ord_unpr = str(int(limit_price)) if limit_price and ord_dvsn == "00" else "0"

    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_cd,
        "PDNO": ticker,
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(int(qty)),  # 국내: 정수 주(株)
        "ORD_UNPR": ord_unpr,
    }

    resp = httpx.post(
        f"{_base_url()}/uapi/domestic-stock/v1/trading/order-cash",
        headers=_headers(tr_id),
        json=body,
        timeout=10,
    )
    resp.raise_for_status()
    data = _check_response(resp.json(), f"domestic order {side} {ticker}")

    output = data.get("output", {})
    order_id = output.get("ODNO", output.get("odno", ""))
    krx_fwdg_ord_orgno = output.get("KRX_FWDG_ORD_ORGNO", output.get("krx_fwdg_ord_orgno", ""))

    logger.info(f"KIS 국내 주문 접수: {side} {int(qty)}주 {ticker} [{order_type}] id={order_id}")

    # 체결가 확보 대기 (최대 5초)
    filled_avg_price = _poll_fill_price(order_id, market="KR")

    return {
        "broker_order_id": order_id,
        "krx_fwdg_ord_orgno": krx_fwdg_ord_orgno,
        "ticker": ticker,
        "side": side.lower(),
        "qty": float(int(qty)),
        "order_type": order_type,
        "status": "filled" if filled_avg_price else "accepted",
        "limit_price": limit_price,
        "filled_avg_price": filled_avg_price,
        "market": "KR",
        "currency": "KRW",
    }


def _place_overseas_order(
    ticker: str,
    side: str,
    qty: float,
    order_type: str,
    limit_price: float | None,
) -> dict:
    """해외(미국) 주식 주문."""
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)

    is_buy = side.lower() == "buy"
    if is_buy:
        tr_id = _US_BUY_PAPER if s.kis_paper else _US_BUY_REAL
    else:
        tr_id = _US_SELL_PAPER if s.kis_paper else _US_SELL_REAL

    # 해외: 지정가=00, 시장가=01 (국내와 반대)
    ord_dvsn = "00" if order_type == "limit" and limit_price else "01"
    ord_unpr = f"{limit_price:.2f}" if limit_price and ord_dvsn == "00" else "0"

    body = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_cd,
        "OVRS_EXCG_CD": _DEFAULT_US_EXCHANGE,
        "PDNO": ticker.upper(),
        "ORD_DVSN": ord_dvsn,
        "ORD_QTY": str(int(qty)),  # 해외도 정수 주
        "OVRS_ORD_UNPR": ord_unpr,
        "ORD_SVR_DVSN_CD": "0",
    }

    resp = httpx.post(
        f"{_base_url()}/uapi/overseas-stock/v1/trading/order",
        headers=_headers(tr_id),
        json=body,
        timeout=10,
    )
    resp.raise_for_status()
    data = _check_response(resp.json(), f"overseas order {side} {ticker}")

    output = data.get("output", {})
    order_id = output.get("ODNO", output.get("odno", ""))

    logger.info(f"KIS 해외 주문 접수: {side} {int(qty)}주 {ticker} [{order_type}] id={order_id}")

    # 해외 주문은 야간장 체결이므로 즉시 fill price 확인 불가 → None
    return {
        "broker_order_id": order_id,
        "ticker": ticker.upper(),
        "side": side.lower(),
        "qty": float(int(qty)),
        "order_type": order_type,
        "status": "accepted",
        "limit_price": limit_price,
        "filled_avg_price": None,
        "market": "US",
        "currency": "USD",
    }


def _poll_fill_price(order_id: str, market: str, retries: int = 3) -> float | None:
    """주문 체결가 폴링 (최대 retries * 0.5초 = 1.5초).

    국내 시장가 주문은 즉시 체결되는 경우가 대부분이므로 3회로 제한.
    미체결 시 None 반환 → 스케줄러가 sync_pending_orders()로 추후 갱신.
    """
    for _ in range(retries):
        time.sleep(0.5)
        try:
            order = get_order(order_id, market=market)
            if order.get("filled_avg_price"):
                return order["filled_avg_price"]
        except Exception as e:
            logger.warning(f"fill price poll failed: {e}")
    logger.warning(f"fill price not confirmed after {retries * 0.5}s: order={order_id}")
    return None


# ---------------------------------------------------------------------------
# 포지션 동기화
# ---------------------------------------------------------------------------


def sync_positions() -> list[dict]:
    """KIS 전체 포지션을 받아 로컬 holdings 테이블을 재구성."""
    from . import repository as db

    positions = get_positions()
    return db.rebuild_holdings_from_broker(positions)


# ---------------------------------------------------------------------------
# 현재가 조회
# ---------------------------------------------------------------------------


def get_current_price(ticker: str) -> dict:
    """국내 단일 종목 현재가 조회.

    Returns:
        ticker, price, change, change_rate, volume, market, currency
    """
    if not is_korean_ticker(ticker):
        raise NotImplementedError(f"해외 종목 현재가 조회는 지원하지 않습니다: {ticker}")

    resp = httpx.get(
        f"{_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price",
        headers=_headers(_KR_PRICE_INQUIRY),
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = _check_response(resp.json(), f"inquire-price {ticker}")

    output = data.get("output", {})
    return {
        "ticker": ticker,
        "price": float(output.get("stck_prpr", 0)),  # 주식 현재가
        "change": float(output.get("prdy_vrss", 0)),  # 전일 대비
        "change_rate": float(output.get("prdy_ctrt", 0)),  # 전일 대비율(%)
        "volume": int(output.get("acml_vol", 0) or 0),  # 누적 거래량
        "market": "KR",
        "currency": "KRW",
    }


# ---------------------------------------------------------------------------
# 주문 취소
# ---------------------------------------------------------------------------


def cancel_order(
    order_id: str,
    market: str = "KR",
    krx_fwdg_ord_orgno: str = "",
    ticker: str = "",
) -> dict:
    """미체결 주문 취소.

    Args:
        order_id: 취소할 원주문번호 (broker_order_id)
        market: 'KR' 또는 'US'
        krx_fwdg_ord_orgno: 국내 주문 시 KRX 전송 주문 조직번호
            (place_order 반환값, 없으면 빈 문자열)
        ticker: 해외 주문 취소 시 종목 코드 (필수)

    Returns:
        original_order_id, cancel_order_id, status, market
    """
    s = get_settings()
    cano, acnt_cd = _parse_account(s.kis_account_no)

    if market == "KR":
        tr_id = _KR_CANCEL_PAPER if s.kis_paper else _KR_CANCEL_REAL
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_cd,
            "KRX_FWDG_ORD_ORGNO": krx_fwdg_ord_orgno,
            "ORGN_ODNO": order_id,
            "ORD_DVSN": "00",
            "RVSE_CNCL_DVSN_CD": "02",  # 02 = 취소
            "ORD_QTY": "0",
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y",  # 잔량 전량 취소
            "EXCG_ID_DVSN_CD": "KRX",  # 거래소 ID (KRX: 한국거래소, NXT: 대체거래소, SOR)
        }
        endpoint = f"{_base_url()}/uapi/domestic-stock/v1/trading/order-rvsecncl"
    else:
        tr_id = _US_CANCEL_PAPER if s.kis_paper else _US_CANCEL_REAL
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_cd,
            "OVRS_EXCG_CD": _DEFAULT_US_EXCHANGE,
            "PDNO": ticker.upper(),  # 해외 취소 시 종목코드 필수
            "ORGN_ODNO": order_id,
            "RVSE_CNCL_DVSN_CD": "02",
            "ORD_QTY": "0",
            "OVRS_ORD_UNPR": "0",  # 취소주문 시 "0" 입력
            "MGCO_APTM_ODNO": "",  # 운용사지정주문번호 (일반 주문은 빈 문자열)
            "ORD_SVR_DVSN_CD": "0",
        }
        endpoint = f"{_base_url()}/uapi/overseas-stock/v1/trading/order-rvsecncl"

    resp = httpx.post(endpoint, headers=_headers(tr_id), json=body, timeout=10)
    resp.raise_for_status()
    data = _check_response(resp.json(), f"cancel order {order_id} ({market})")

    output = data.get("output", {})
    cancel_order_id = output.get("ODNO", output.get("odno", ""))

    logger.info(f"KIS 주문 취소: order_id={order_id}, market={market}, cancel_id={cancel_order_id}")
    return {
        "original_order_id": order_id,
        "cancel_order_id": cancel_order_id,
        "status": "canceled",
        "market": market,
    }
