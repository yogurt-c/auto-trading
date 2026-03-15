"""보유 종목 — Alpaca 단일 소스 (읽기 전용)."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from core import alpaca_client
from core.database import init_db
from core.portfolio import get_all_holdings, get_transactions

init_db()

_SYNC_TTL = 30  # seconds

st.set_page_config(page_title="보유 종목", page_icon=None, layout="wide")
st.title("보유 종목")
st.caption("Alpaca 실제 포지션과 자동 동기화됩니다. 수동 편집은 지원되지 않습니다.")

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- Alpaca 실시간 포지션 자동 동기화 (30초 TTL)\n"
        "- 전체 거래 내역 조회"
    )

# ---------------------------------------------------------------------------
# TTL 기반 자동 동기화
# ---------------------------------------------------------------------------

last_sync = st.session_state.get("holdings_last_sync", 0)
if time.time() - last_sync > _SYNC_TTL:
    try:
        alpaca_client.sync_positions()
        st.session_state["holdings_last_sync"] = time.time()
    except ValueError as e:
        st.warning(f"Alpaca 미설정 — 기존 데이터 표시: {e}")
    except Exception as e:
        st.warning(f"Alpaca 동기화 실패 (기존 데이터 표시): {e}")

col_refresh, col_info = st.columns([1, 5])
if col_refresh.button("Alpaca에서 동기화"):
    try:
        alpaca_client.sync_positions()
        st.session_state["holdings_last_sync"] = time.time()
        st.success("동기화 완료.")
        st.rerun()
    except Exception as e:
        st.error(f"동기화 실패: {e}")

# ---------------------------------------------------------------------------
# 보유 종목 테이블 (읽기 전용)
# ---------------------------------------------------------------------------

st.subheader("현재 보유 종목")
holdings = get_all_holdings()

if not holdings:
    st.info("보유 종목이 없습니다. Alpaca 포지션이 없거나 아직 동기화되지 않았습니다.")
else:
    df = pd.DataFrame(holdings)[["ticker", "shares", "avg_price"]]
    df.columns = ["티커", "수량", "평균 매입가 ($)"]
    st.dataframe(
        df.style.format({"수량": "{:.4f}", "평균 매입가 ($)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# 거래 내역
# ---------------------------------------------------------------------------

st.subheader("거래 내역")
txns = get_transactions(limit=50)

if txns:
    txn_df = pd.DataFrame(txns)
    txn_df = txn_df[["executed_at", "ticker", "action", "shares", "price", "total"]]
    txn_df.columns = ["날짜", "티커", "구분", "수량", "가격", "거래금액"]
    st.dataframe(
        txn_df.style.format({"가격": "${:,.2f}", "거래금액": "${:,.2f}", "수량": "{:.4f}"}),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("거래 내역이 없습니다.")
