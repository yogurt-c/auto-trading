"""보유 종목 — 종목 추가 · 수정 · 삭제, 거래 내역."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.database import init_db
from core.portfolio import (
    get_all_holdings,
    get_transactions,
    remove_holding,
    update_holding,
    upsert_holding,
)

init_db()

st.set_page_config(page_title="보유 종목", page_icon=None, layout="wide")
st.title("보유 종목")
st.caption("보유 중인 미국 주식/ETF를 관리합니다. 매수 시 수량을 추가하면 평균 매입가가 자동 계산됩니다.")

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- 종목 추가 (매수 시 가중평균 자동 계산)\n"
        "- 수량 · 평균가 직접 수정\n"
        "- 종목 삭제\n"
        "- 전체 거래 내역 조회"
    )

# ---------------------------------------------------------------------------
# 종목 추가 폼
# ---------------------------------------------------------------------------

with st.expander("종목 추가 / 매수 입력", expanded=False):
    with st.form("add_holding_form"):
        c1, c2, c3 = st.columns(3)
        ticker = c1.text_input("티커", placeholder="AAPL").strip().upper()
        shares = c2.number_input("수량", min_value=0.0001, step=0.01, format="%.4f")
        price = c3.number_input("매수가 ($)", min_value=0.01, step=0.01, format="%.2f")
        submitted = st.form_submit_button("추가", type="primary")

    if submitted:
        if not ticker:
            st.error("티커를 입력하세요.")
        elif shares <= 0 or price <= 0:
            st.error("수량과 매수가는 0보다 커야 합니다.")
        else:
            result = upsert_holding(ticker, shares, price)
            st.success(
                f"{ticker} {shares}주 @ ${price:.2f} 추가 완료. "
                f"평균 매입가: ${result['avg_price']:.2f} (총 {result['shares']:.4f}주)"
            )
            st.rerun()

# ---------------------------------------------------------------------------
# 보유 종목 테이블
# ---------------------------------------------------------------------------

st.subheader("현재 보유 종목")
holdings = get_all_holdings()

if not holdings:
    st.info("보유 종목이 없습니다. 위 폼에서 종목을 추가하세요.")
else:
    for row in holdings:
        with st.container():
            col_ticker, col_shares, col_price, col_edit, col_del = st.columns([2, 2, 2, 1, 1])
            col_ticker.markdown(f"**{row['ticker']}**")
            col_shares.write(f"{row['shares']:.4f}주")
            col_price.write(f"평균 ${row['avg_price']:.2f}")

            if col_edit.button("수정", key=f"edit_{row['ticker']}"):
                st.session_state[f"editing_{row['ticker']}"] = True

            if col_del.button("삭제", key=f"del_{row['ticker']}"):
                st.session_state[f"confirm_del_{row['ticker']}"] = True

            if st.session_state.get(f"confirm_del_{row['ticker']}"):
                st.warning(f"**{row['ticker']}**을(를) 포트폴리오에서 삭제하시겠습니까? 되돌릴 수 없습니다.")
                yes_col, no_col = st.columns(2)
                if yes_col.button("삭제", key=f"yes_del_{row['ticker']}", type="primary"):
                    remove_holding(row["ticker"])
                    st.session_state.pop(f"confirm_del_{row['ticker']}", None)
                    st.success(f"{row['ticker']} 삭제 완료.")
                    st.rerun()
                if no_col.button("취소", key=f"no_del_{row['ticker']}"):
                    st.session_state.pop(f"confirm_del_{row['ticker']}", None)
                    st.rerun()

            if st.session_state.get(f"editing_{row['ticker']}"):
                with st.form(f"edit_form_{row['ticker']}"):
                    e1, e2 = st.columns(2)
                    new_shares = e1.number_input(
                        "수량", value=float(row["shares"]),
                        min_value=0.0001, step=0.01, format="%.4f",
                        key=f"es_{row['ticker']}",
                    )
                    new_price = e2.number_input(
                        "평균 매입가 ($)", value=float(row["avg_price"]),
                        min_value=0.01, step=0.01, format="%.2f",
                        key=f"ep_{row['ticker']}",
                    )
                    save, cancel = st.columns(2)
                    if save.form_submit_button("저장", type="primary"):
                        update_holding(row["ticker"], new_shares, new_price)
                        st.session_state.pop(f"editing_{row['ticker']}", None)
                        st.success(f"{row['ticker']} 수정 완료.")
                        st.rerun()
                    if cancel.form_submit_button("취소"):
                        st.session_state.pop(f"editing_{row['ticker']}", None)
                        st.rerun()

        st.divider()

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
