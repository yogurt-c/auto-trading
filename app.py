"""Streamlit 메인 진입점."""

import streamlit as st

from core.config import get_settings
from core.database import init_db

st.set_page_config(
    page_title="AI 포트폴리오 매니저",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

from core.scheduler import ensure_started as _ensure_scheduler
_ensure_scheduler()

if not get_settings().is_configured:
    st.sidebar.error("API 키 미설정 — 설정 페이지에서 입력하세요.")

st.title("AI 포트폴리오 매니저")
st.markdown(
    """
    Claude AI 기반 미국 주식/ETF 포트폴리오 관리 툴입니다.
    좌측 사이드바에서 페이지를 선택하세요.

    | 페이지 | 설명 |
    |--------|------|
    | **설정** | Anthropic · Alpaca API 키 등록 (최초 1회) |
    | **대시보드** | 포트폴리오 전체 현황, 수익률, 자산 배분 차트 |
    | **보유 종목** | 종목 추가 · 수정 · 삭제, 거래 내역 확인 |
    | **AI 분석** | AI와 대화하며 포트폴리오 분석 및 매매 전략 수립 |
    | **자동 매매** | 전략 활성화 · 정지, Alpaca 잔고 확인, 매매 로그 |
    """
)
