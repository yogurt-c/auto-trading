"""설정 페이지 — API 키를 로컬 DB에 저장."""

import streamlit as st

from core.alpaca_client import reset_client
from core.config import REQUIRED_KEYS, get_settings, reload_settings
from core.database import init_db
from core.portfolio import get_all_settings, save_setting

init_db()

st.set_page_config(page_title="설정", page_icon=None, layout="wide")
st.title("설정")
st.caption("API 키는 로컬 DB에 저장됩니다. 최초 1회만 입력하면 이후 자동으로 불러옵니다.")

with st.sidebar:
    st.markdown("### 이 페이지에서 할 수 있는 것")
    st.markdown(
        "- Anthropic API 키 등록 (AI 채팅 · 분석에 사용)\n"
        "- Alpaca API 키 등록 (자동 매매에 사용)\n"
        "- Paper Trading / 실거래 전환"
    )

current = get_all_settings()

with st.form("settings_form"):
    st.subheader("Anthropic")
    anthropic_key = st.text_input(
        "ANTHROPIC_API_KEY",
        value=current.get("ANTHROPIC_API_KEY", ""),
        type="password",
        placeholder="sk-ant-...",
        help="https://console.anthropic.com → API Keys",
    )

    st.subheader("Alpaca")
    alpaca_key = st.text_input(
        "ALPACA_API_KEY",
        value=current.get("ALPACA_API_KEY", ""),
        type="password",
        placeholder="PK...",
        help="alpaca.markets → Paper Trading → Your API Keys",
    )
    alpaca_secret = st.text_input(
        "ALPACA_SECRET_KEY",
        value=current.get("ALPACA_SECRET_KEY", ""),
        type="password",
    )
    alpaca_paper = st.toggle(
        "Paper Trading (가상 매매 모드)",
        value=current.get("ALPACA_PAPER", "true").lower() == "true",
        help="OFF로 바꾸면 실거래 계정을 사용합니다. 신중하게 선택하세요.",
    )

    saved = st.form_submit_button("저장", type="primary")

if saved:
    if anthropic_key:
        save_setting("ANTHROPIC_API_KEY", anthropic_key)
    if alpaca_key:
        save_setting("ALPACA_API_KEY", alpaca_key)
    if alpaca_secret:
        save_setting("ALPACA_SECRET_KEY", alpaca_secret)
    save_setting("ALPACA_PAPER", "true" if alpaca_paper else "false")

    reset_client()
    reload_settings()
    st.success("저장되었습니다.")
    st.rerun()

st.markdown("---")
st.subheader("현재 등록 상태")
settings = get_settings()
for key in REQUIRED_KEYS:
    val = getattr(settings, key.lower())
    if val:
        masked = val[:8] + "·····" + val[-4:]
        st.success(f"**{key}** — {masked}")
    else:
        st.error(f"**{key}** — 미등록")
