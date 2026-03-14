"""AI 분석 — 오케스트레이터 에이전트와 대화."""

from __future__ import annotations

import streamlit as st

from core.agent import stream_orchestrator
from core.database import init_db

init_db()

st.set_page_config(page_title="AI 분석", page_icon=None, layout="wide")
st.title("AI 분석")
st.caption(
    "AI 포트폴리오 매니저와 대화하세요. "
    "포트폴리오 분석, 실시간 시세 조회, 매매 전략 수립까지 자연어로 요청할 수 있습니다."
)

# ---------------------------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------------------------

if "chat_history" not in st.session_state:
    st.session_state.chat_history: list[dict] = []
if "generating" not in st.session_state:
    st.session_state.generating = False
if "pending_input" not in st.session_state:
    st.session_state.pending_input = None

generating = st.session_state.generating

# ---------------------------------------------------------------------------
# 사이드바
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- 포트폴리오 전체 분석 요청\n"
        "- 특정 종목 시세 · 뉴스 조회\n"
        "- 매매 전략 수립 (Strategy Advisor 서브에이전트)\n"
        "- 리밸런싱 · 리스크 관리 조언"
    )
    st.markdown("---")
    st.markdown("### 빠른 질문")
    quick_prompts = [
        "포트폴리오 현황을 분석해줘",
        "전체 포트폴리오 리밸런싱 전략 제안해줘",
        "현재 보유 중인 가장 위험한 종목은?",
    ]
    for prompt in quick_prompts:
        if st.button(prompt, use_container_width=True, disabled=generating):
            st.session_state.pending_input = prompt
            st.session_state.generating = True
            st.rerun()

    st.markdown("---")
    if st.button("대화 기록 초기화", use_container_width=True, disabled=generating):
        st.session_state.chat_history = []
        st.rerun()

# ---------------------------------------------------------------------------
# 대화 기록 렌더링
# ---------------------------------------------------------------------------

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# 응답 생성
# ---------------------------------------------------------------------------

def _stream_response(user_msg: str) -> None:
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_history
    ]

    with st.chat_message("user"):
        st.markdown(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("응답 생성 중…"):
            placeholder = st.empty()
            full_response = ""
            try:
                for chunk in stream_orchestrator(user_msg, history):
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
            except Exception as e:
                full_response = f"오류: {e}"
                placeholder.markdown(full_response)

    st.session_state.chat_history.append({"role": "user", "content": user_msg})
    st.session_state.chat_history.append({"role": "assistant", "content": full_response})


if generating and st.session_state.pending_input:
    pending = st.session_state.pending_input
    st.session_state.pending_input = None
    st.session_state.generating = False
    _stream_response(pending)
    st.rerun()

# ---------------------------------------------------------------------------
# 사용자 입력
# ---------------------------------------------------------------------------

user_input = st.chat_input(
    "포트폴리오에 대해 무엇이든 물어보세요…" if not generating else "응답 생성 중…",
    disabled=generating,
)

if user_input:
    st.session_state.pending_input = user_input
    st.session_state.generating = True
    st.rerun()
