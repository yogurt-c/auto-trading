"""대시보드 — 포트폴리오 현황, 수익률, 자산 배분."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from core.database import init_db
from core.market import get_current_prices
from core.portfolio import get_all_holdings

init_db()

st.set_page_config(page_title="대시보드", page_icon=None, layout="wide")
st.title("대시보드")
st.caption("보유 종목의 평가 금액, 수익률, 자산 배분 현황을 한눈에 확인합니다.")

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- 총 평가액 · 투자금 · 손익 확인\n"
        "- 실시간 시세 자동 조회 (Yahoo Finance)\n"
        "- 자산 배분 파이차트\n"
        "- 종목별 수익률 바차트"
    )
    st.markdown("---")
    st.markdown("### 자동 새로고침")
    intervals = {"사용 안 함": None, "30초": 30, "1분": 60, "5분": 300, "10분": 600}
    selected = st.selectbox("주기", list(intervals.keys()), index=2)
    refresh_every = intervals[selected]

holdings = get_all_holdings()

if not holdings:
    st.info("보유 종목이 없습니다. **보유 종목** 페이지에서 먼저 종목을 추가하세요.")
    st.stop()

tickers = [h["ticker"] for h in holdings]


@st.fragment(run_every=refresh_every)
def price_dashboard():
    prices = get_current_prices(tickers)
    failed = [t for t in tickers if t not in prices]

    # 조회 실패 종목 수동 입력
    current_prices = dict(prices)
    if failed:
        st.warning(f"시세 조회 실패: {', '.join(failed)} — 직접 입력하세요.")
        fail_cols = st.columns(min(len(failed), 4))
        df_h = pd.DataFrame(holdings)
        for i, ticker in enumerate(failed):
            with fail_cols[i % 4]:
                current_prices[ticker] = st.number_input(
                    ticker,
                    min_value=0.01,
                    value=float(df_h.loc[df_h["ticker"] == ticker, "avg_price"].iloc[0]),
                    step=0.01, format="%.2f",
                    key=f"manual_{ticker}",
                )

    # 계산
    df = pd.DataFrame(holdings)
    df["current_price"] = df["ticker"].map(current_prices)
    df["market_value"] = df["shares"] * df["current_price"]
    df["cost_basis"] = df["shares"] * df["avg_price"]
    df["pnl"] = df["market_value"] - df["cost_basis"]
    df["pnl_pct"] = (df["pnl"] / df["cost_basis"] * 100).round(2)

    total_value = df["market_value"].sum()
    total_cost = df["cost_basis"].sum()
    total_pnl = df["pnl"].sum()
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    # 메트릭 카드
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 평가액", f"${total_value:,.2f}")
    col2.metric("총 투자금", f"${total_cost:,.2f}")
    col3.metric("총 손익", f"${total_pnl:,.2f}", delta=f"{total_pnl_pct:.2f}%", delta_color="normal")
    col4.metric("보유 종목 수", str(len(holdings)))

    st.markdown("---")

    # 차트
    chart_col, table_col = st.columns([1, 2])

    with chart_col:
        st.subheader("자산 배분")
        fig = px.pie(
            df, names="ticker", values="market_value",
            hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, margin=dict(t=20, b=20, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    with table_col:
        st.subheader("종목별 상세")
        display_df = df[["ticker", "shares", "avg_price", "current_price", "market_value", "pnl", "pnl_pct"]].copy()
        display_df.columns = ["티커", "수량", "평균 매입가", "현재가", "평가금액", "손익($)", "손익(%)"]

        def _color_pnl(val):
            return f"color: {'green' if val >= 0 else 'red'}"

        st.dataframe(
            display_df.style
            .format({
                "평균 매입가": "${:,.2f}", "현재가": "${:,.2f}",
                "평가금액": "${:,.2f}", "손익($)": "${:,.2f}", "손익(%)": "{:.2f}%",
            })
            .map(_color_pnl, subset=["손익($)", "손익(%)"]),
            use_container_width=True, hide_index=True,
        )

    st.markdown("---")
    st.subheader("종목별 수익률")
    fig2 = px.bar(
        df, x="ticker", y="pnl_pct",
        color="pnl_pct",
        color_continuous_scale=["red", "white", "green"],
        color_continuous_midpoint=0,
        labels={"ticker": "티커", "pnl_pct": "수익률(%)"},
        text="pnl_pct",
    )
    fig2.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig2.update_layout(coloraxis_showscale=False, margin=dict(t=20))
    st.plotly_chart(fig2, use_container_width=True)

    if refresh_every:
        st.caption(f"{selected}마다 자동 갱신 중")


price_dashboard()
