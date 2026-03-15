"""자동 매매 — 전략 관리, Alpaca Paper Trading."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.alpaca_client import get_account, get_positions
from core.database import init_db
from core.portfolio import (
    delete_strategy,
    get_scheduler_runs,
    get_setting,
    get_strategies,
    get_trade_logs,
    save_setting,
    update_strategy_status,
)
from core.scheduler import ensure_started, get_status

init_db()

st.set_page_config(page_title="자동 매매", page_icon=None, layout="wide")
st.title("자동 매매")
st.caption("AI가 수립한 전략을 기반으로 Alpaca Paper Trading 계좌에서 자동으로 주문을 실행합니다.")

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- Alpaca 계좌 잔고 · 포지션 확인\n"
        "- 매매 전략 활성화 · 정지 · 완료 · 삭제\n"
        "- 스케줄러 설정 및 실행 이력 확인\n"
        "- 최근 주문 실행 로그 확인"
    )

# ---------------------------------------------------------------------------
# Alpaca 계좌 현황
# ---------------------------------------------------------------------------

st.subheader("Alpaca 계좌 현황")

try:
    acct = get_account()
    positions = get_positions()

    m1, m2, m3 = st.columns(3)
    m1.metric("현금", f"${acct['cash']:,.2f}")
    m2.metric("포트폴리오 평가액", f"${acct['portfolio_value']:,.2f}")
    m3.metric("주문 가능 금액", f"${acct['buying_power']:,.2f}")

    if positions:
        st.markdown("**보유 포지션**")
        pos_df = pd.DataFrame(positions)
        pos_df.columns = ["티커", "수량", "평균 매입가", "현재가", "평가금액", "미실현 손익($)", "미실현 손익(%)"]
        st.dataframe(
            pos_df.style.format({
                "평균 매입가": "${:,.2f}", "현재가": "${:,.2f}",
                "평가금액": "${:,.2f}", "미실현 손익($)": "${:,.2f}",
                "미실현 손익(%)": "{:.2%}",
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Alpaca 계좌에 보유 포지션이 없습니다.")
except Exception as e:
    st.warning(f"Alpaca 연결 실패: {e}")
    st.info("설정 페이지에서 ALPACA_API_KEY와 ALPACA_SECRET_KEY를 등록하세요.")

# ---------------------------------------------------------------------------
# Trade Executor
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Trade Executor")
st.caption("활성 전략의 진입·청산 조건을 확인하고, 충족된 전략에 대해 자동으로 주문을 실행합니다.")

# 토글 상태를 settings 테이블에서 읽어오기
db_enabled = get_setting("scheduler_enabled") == "true"
auto_enabled = st.toggle(
    "자동 매매 활성화",
    value=db_enabled,
    help="활성화하면 설정된 간격으로 Trade Executor 에이전트가 자동 실행됩니다.",
)
if auto_enabled != db_enabled:
    save_setting("scheduler_enabled", "true" if auto_enabled else "false")
    ensure_started()
    st.rerun()

if not auto_enabled:
    st.info("**자동 매매 활성화** 토글을 켜면 자동 스케줄링이 활성화됩니다.")

# ---------------------------------------------------------------------------
# 스케줄러 설정 (활성화 상태일 때만 표시)
# ---------------------------------------------------------------------------

if auto_enabled:
    st.markdown("#### 스케줄러 설정")

    INTERVAL_OPTIONS = [5, 15, 30, 60]
    current_interval_raw = get_setting("scheduler_interval_minutes")
    current_interval = int(current_interval_raw) if current_interval_raw else 30

    selected_interval = st.selectbox(
        "실행 간격",
        options=INTERVAL_OPTIONS,
        index=INTERVAL_OPTIONS.index(current_interval) if current_interval in INTERVAL_OPTIONS else 2,
        format_func=lambda x: f"{x}분",
        key="scheduler_interval_select",
    )
    if selected_interval != current_interval:
        save_setting("scheduler_interval_minutes", str(selected_interval))
        ensure_started()
        st.rerun()

    # 스케줄러 상태 표시
    status = get_status()
    if status["running"]:
        next_run = status["next_run"]
        next_run_str = next_run.strftime("%H:%M:%S") if next_run else "—"
        if status["market_open"]:
            st.success(f"실행 중 · 다음 실행: {next_run_str}")
        else:
            st.warning(f"실행 중 · 다음 실행: {next_run_str}")
            st.caption("현재 장 외 시간입니다. NYSE 개장 시간(평일 09:30~16:00 ET)에만 주문이 처리됩니다.")
    else:
        st.error("정지됨")

# ---------------------------------------------------------------------------
# 스케줄러 실행 이력
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("스케줄러 실행 이력")
st.caption("실행 이력은 Trade Executor 에이전트의 판단 컨텍스트로 활용됩니다.")

runs = get_scheduler_runs(limit=20)
if runs:
    run_rows = []
    for r in runs:
        run_rows.append({
            "시작시각": r.get("started_at"),
            "종료시각": r.get("finished_at"),
            "상태": r["status"],
            "체크 전략 수": r.get("strategies_checked", 0),
            "주문 수": r.get("orders_placed", 0),
            "오류": r.get("error_message") or "",
            "요약": r.get("summary") or "",
        })

    run_df = pd.DataFrame(run_rows)
    st.dataframe(
        run_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "요약": st.column_config.TextColumn("요약", width="large"),
            "오류": st.column_config.TextColumn("오류", width="medium"),
        },
    )
else:
    st.info("아직 스케줄러 실행 이력이 없습니다. 자동 매매를 활성화하면 이력이 쌓입니다.")

# ---------------------------------------------------------------------------
# 전략 목록
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("매매 전략 목록")
st.caption("AI 분석 페이지에서 수립된 전략이 여기에 표시됩니다. 각 전략을 활성화·정지·완료 처리할 수 있습니다.")

all_strategies = get_strategies()

if not all_strategies:
    st.info("저장된 전략이 없습니다. AI 분석 페이지에서 '전략 만들어줘'라고 요청하세요.")
else:
    tab_active, tab_paused, tab_completed = st.tabs(["활성", "정지", "완료"])

    STATUS_LABELS = {"active": "활성", "paused": "정지", "completed": "완료"}

    for tab, status in [(tab_active, "active"), (tab_paused, "paused"), (tab_completed, "completed")]:
        with tab:
            filtered = [s for s in all_strategies if s["status"] == status]
            if not filtered:
                st.info(f"{STATUS_LABELS[status]} 상태의 전략이 없습니다.")
                continue

            for strat in filtered:
                with st.expander(
                    f"**{strat['name']}** "
                    + (f"— {strat['ticker']}" if strat.get("ticker") else "— 포트폴리오 전체")
                    + f" ({strat['strategy_type']})",
                    expanded=False,
                ):
                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.markdown(f"**설명:** {strat['description']}")
                        if strat.get("ai_rationale"):
                            st.markdown(f"**AI 근거:** {strat['ai_rationale']}")
                        if strat.get("last_checked_at"):
                            st.caption(f"마지막 체크: {strat['last_checked_at']}")
                        if strat.get("last_triggered_at"):
                            st.caption(f"마지막 주문 발생: {strat['last_triggered_at']}")
                    with c_right:
                        params = {
                            "진입 하락률(%)": strat.get("entry_price_drop_pct"),
                            "진입 RSI <": strat.get("entry_rsi_below"),
                            "목표 수익률(%)": strat.get("take_profit_pct"),
                            "손절률(%)": strat.get("stop_loss_pct"),
                            "매도 비율": strat.get("sell_ratio"),
                            "DCA 금액($)": strat.get("dca_amount_usd"),
                            "DCA 주기(일)": strat.get("dca_frequency_days"),
                            "최대 투자 한도($)": strat.get("max_position_usd"),
                        }
                        for k, v in params.items():
                            if v is not None:
                                st.write(f"**{k}:** {v}")

                    btn_cols = st.columns(4)
                    if status != "active" and btn_cols[0].button("활성화", key=f"act_{strat['id']}"):
                        update_strategy_status(strat["id"], "active")
                        st.rerun()
                    if status != "paused" and btn_cols[1].button("정지", key=f"pause_{strat['id']}"):
                        update_strategy_status(strat["id"], "paused")
                        st.rerun()
                    if status != "completed" and btn_cols[2].button("완료", key=f"complete_{strat['id']}"):
                        update_strategy_status(strat["id"], "completed")
                        st.rerun()
                    if btn_cols[3].button("삭제", key=f"del_{strat['id']}", type="secondary"):
                        delete_strategy(strat["id"])
                        st.rerun()

# ---------------------------------------------------------------------------
# 매매 로그
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("최근 매매 로그")
st.caption("Trade Executor가 실행한 주문 내역입니다.")

logs = get_trade_logs(limit=50)
if logs:
    log_df = pd.DataFrame(logs)
    log_df = log_df[["executed_at", "ticker", "side", "qty", "order_type", "limit_price", "status", "ai_reasoning"]]
    log_df.columns = ["날짜", "티커", "매수/매도", "수량", "주문유형", "지정가", "상태", "AI 판단 근거"]

    def _color_status(val):
        colors = {"filled": "green", "failed": "red", "cancelled": "orange", "pending": "blue"}
        return f"color: {colors.get(val, 'black')}"

    st.dataframe(
        log_df.style
        .format({"지정가": lambda x: f"${x:.2f}" if x else "—", "수량": "{:.4f}"})
        .map(_color_status, subset=["상태"]),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("아직 실행된 매매 내역이 없습니다.")
