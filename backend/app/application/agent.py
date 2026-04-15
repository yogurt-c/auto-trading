"""Orchestrator + sub-agent implementation using Anthropic SDK.

Architecture:
  Orchestrator  → general Q&A, portfolio analysis
                → delegates to sub-agents via the 'task' tool
  Strategy Advisor sub-agent  → strategy discussion + save_strategy
  Trade Executor sub-agent    → condition checking + place_order

Token optimizations:
  - Model tiering: Trade Executor uses Haiku; others use Sonnet
  - Per-agent max_tokens / max_iterations limits
  - Prompt caching on system prompts and tool schemas
  - Cost logging per API call (debug level)
  - Retry on transient errors only (RateLimitError, APIConnectionError, InternalServerError)
"""

from __future__ import annotations

import json
import queue as _queue
import threading
import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

import anthropic
from loguru import logger

from .tools import (
    PORTFOLIO_TOOLS,
    STRATEGY_TOOLS,
    TRADE_TOOLS,
    WEB_SEARCH_TOOL,
    dispatch_tool,
)

_HISTORY_LIMIT = 20  # orchestrator에 전달할 최대 메시지 수

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

# Pricing: (input $/1M tokens, output $/1M tokens) — 2025-2026
_PRICING: dict[str, tuple[float, float]] = {
    SONNET: (3.00, 15.00),
    HAIKU: (0.80, 4.00),
}

_RETRYABLE_ERRORS = (
    anthropic.RateLimitError,
    anthropic.APIConnectionError,
    anthropic.InternalServerError,
)


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = _PRICING.get(model, (3.00, 15.00))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def _api_create_with_retry(client: anthropic.Anthropic, **kwargs) -> Any:
    """Transient errors (rate limit, connection, 5xx): max 3 retries with exponential backoff.

    Fails fast on AuthenticationError, BadRequestError, and other permanent failures.
    Logs token usage and estimated USD cost after each successful call.
    """
    for attempt in range(3):
        try:
            response = client.messages.create(**kwargs)
            model = kwargs.get("model", "unknown")
            usage = response.usage
            cost = _compute_cost(model, usage.input_tokens, usage.output_tokens)
            logger.info(
                f"api call: model={model} "
                f"in={usage.input_tokens} out={usage.output_tokens} "
                f"cost=${cost:.4f}"
            )
            return response
        except _RETRYABLE_ERRORS as e:
            if attempt == 2:
                raise
            wait = 2**attempt * 15  # 15s, 30s
            logger.warning(
                f"transient error ({type(e).__name__}), retrying in {wait}s "
                f"(attempt {attempt + 1}/3)"
            )
            time.sleep(wait)
    raise RuntimeError("_api_create_with_retry: retry loop exhausted without result")


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ORCHESTRATOR_PROMPT = """\
You are a professional portfolio manager assistant.
You help users understand their portfolio performance, analyze holdings,
and answer market questions.

You have access to:
- get_portfolio: retrieve current holdings
- web_search: look up current prices, news, and market data
- task: delegate complex sub-tasks to specialized agents

When the user wants to create or manage a trading strategy,
delegate to the "strategy-advisor" sub-agent.
When the user asks to execute trades or check automated trading,
delegate to the "trade-executor" sub-agent.

Always be concise, data-driven, and mention specific numbers when analyzing the portfolio.
When citing prices or news, use web_search to get current data.

Response format:
- Use clean markdown only (headers, bold, tables, bullet lists)
- Do not use any emoji or icons in your responses
"""

STRATEGY_ADVISOR_PROMPT = """\
You are a trading strategy advisor specialized in Korean and US equities and ETFs.
Your goal is to help users build concrete, executable trading strategies via KIS (한국투자증권).

Ticker convention:
- Korean stocks: 6-digit numbers (e.g., 005930 for Samsung) → market=KR, currency=KRW
- US stocks: alphabetic tickers (e.g., AAPL, TSLA) → market=US, currency=USD

Workflow:
1. Discuss the strategy with the user (entry conditions, exit conditions, position sizing)
2. Use web_search to research the ticker if needed
3. Identify the correct market (KR/US) and currency (KRW/USD) from the ticker
4. Summarize the agreed strategy clearly
5. Before calling save_strategy, verify ALL of the following constraints are satisfied.
   If any constraint would be violated, fix the value first — do NOT call save_strategy
   with invalid parameters:
   - Non-DCA strategies (momentum, value, stop_loss, take_profit, custom): at least ONE
     entry condition from the list below must be set
   - DCA strategies: dca_amount and dca_frequency_days are both required
   - dca_amount must not exceed max_position (if max_position is set)
   - stop_loss_pct must be strictly less than take_profit_pct (e.g., stop=-7, take=+10 ✓)
   - sell_ratio must be between 0 (exclusive) and 1 (inclusive)
   - dca_frequency_days must be a positive integer
6. Call save_strategy to persist the structured parameters
   - If success is false and errors exist: autonomously fix the invalid parameters
     based on the error messages and call save_strategy again immediately.
     Do NOT ask the user — resolve blocking errors on your own.
   - If success is true and warnings exist: proceed to step 7, then inform
     the user about the warnings so they can decide whether to adjust.
7. Confirm the strategy was saved — show key parameters in a table including market and currency

Available entry conditions (non-DCA strategies must include at least one):
- entry_price_drop_pct: float, MUST be negative — buy when price drops N% from 30-day high
  (e.g., -5.0 = buy on 5% dip). Positive values are invalid.
- entry_rsi_below: float, 0-100 — buy when RSI(14) ≤ threshold (e.g., 30.0 for oversold)
- entry_bb_lower_touch: bool — buy when price touches or breaks below Bollinger lower band
- entry_macd_hist_positive: bool — buy when MACD histogram turns positive (bearish→bullish)
- entry_disparity_below: float, MUST be negative — buy when 20-day disparity ≤ threshold
  (e.g., -5.0 = buy when price is 5% below 20-day MA). Positive values are invalid.
- entry_volume_surge: float, MUST be > 1.0 — buy when volume >= Nx 20-day average
  (e.g., 2.0 = buy on 2x volume surge). Values ≤ 1.0 are invalid.
- entry_sma_cross: int, MUST be 20 or 60 — buy when price crosses above SMA(N).
  Only 20 and 60 are supported; any other value is invalid.

Other structured fields:
- take_profit_pct: float — exit when P&L ≥ N% (e.g., 10.0)
- stop_loss_pct: float — exit when P&L ≤ N% (e.g., -7.0); must be < take_profit_pct
- sell_ratio: float (0, 1] — fraction of position to sell on exit signal (e.g., 1.0 = full)
- dca_amount: float — amount per DCA buy in currency units (required for DCA)
- dca_frequency_days: int, positive — interval between DCA buys (required for DCA)
- max_position: float — maximum total exposure in currency units; dca_amount must not exceed this
- market: 'KR' or 'US'
- currency: 'KRW' or 'USD'

Be proactive about risk management: always recommend a stop-loss.

Response format:
- Use clean markdown only (headers, bold, tables, bullet lists)
- Do not use any emoji or icons in your responses
- When confirming a saved strategy, always include a parameter table:

| 항목 | 값 |
|------|---|
| 시장 | KR / US |
| 통화 | KRW / USD |
| 진입 조건 | ... |
| 익절 | ... |
| 손절 | ... |
| DCA 금액 | ₩50,000 or $50 |
| 최대 포지션 | ₩1,000,000 or $1,000 |
"""

TRADE_EXECUTOR_PROMPT = """\
You are an automated trade execution agent using KIS (한국투자증권) API.
Your job is to review active strategies and execute orders when conditions are met.

Ticker convention:
- Korean stocks (market=KR): 6-digit numbers (e.g., 005930). Trading hours: KST 09:00-15:30
- US stocks (market=US): alphabetic tickers (e.g., AAPL). Trading hours: ET 09:30-16:00

Workflow:
1. Call get_scheduler_runs(limit=10) to review recent execution history
   - Check if previous runs successfully executed planned strategies
   - Identify any patterns of missed signals or repeated failures
2. Call get_strategies(status='active') to get all active strategies
3. Call get_broker_account() to check current positions and buying power
4. For each strategy, call evaluate_strategy(strategy_id) to check conditions
   - For DCA strategies: also call check_dca_due(strategy_id); only proceed if is_due is true
   - Do NOT use web_search to manually fetch prices or compute conditions
5. If evaluate_strategy returns entry_triggered=true or exit_triggered=true, call place_order
   - Always pass max_position from the strategy if it is set
   - Check market hours before placing: KR strategies only during KST 09:00-15:30,
     US strategies only during ET 09:30-16:00
6. In your summary, mention: which strategies were checked, what conditions
   were evaluated, which orders were placed, and any concerns about strategy
   execution consistency based on historical runs.

Rules:
- NEVER exceed max_position per strategy (amounts are in the strategy's currency: KRW or USD)
- Always include ai_reasoning explaining why the order was triggered
- If conditions are ambiguous, err on the side of NOT trading
- For KIS paper trading (모의투자): overseas stock orders may not be supported

응답 형식:
- 반드시 한국어로 작성하세요
- 마크다운 형식만 사용하세요 (헤더, 굵게, 표, 불릿 리스트)
- 이모지나 아이콘은 사용하지 마세요
- 다음 구조를 따르세요:

## 실행 요약
## 전략 평가 결과
| 전략명 | 시장 | 조건 | 결과 | 조치 |
## 주문 내역
| 종목 | 시장 | 유형 | 수량 | 가격 | 통화 | 상태 |
## 리스크 및 주의사항
"""

# ---------------------------------------------------------------------------
# Prompt caching helpers
# ---------------------------------------------------------------------------


def _cached_system(prompt: str) -> list[dict]:
    """Wrap system prompt as a single cacheable content block."""
    return [{"type": "text", "text": prompt, "cache_control": {"type": "ephemeral"}}]


def _cached_tools(tools: list[dict]) -> list[dict]:
    """Add cache_control to the last custom tool (has input_schema).

    Built-in server tools like web_search use a 'type' field instead of
    'input_schema' and do not support cache_control.
    """
    result = [dict(t) for t in tools]
    for i in range(len(result) - 1, -1, -1):
        if "input_schema" in result[i]:
            result[i] = {**result[i], "cache_control": {"type": "ephemeral"}}
            break
    return result


# ---------------------------------------------------------------------------
# Sub-agent definitions
# ---------------------------------------------------------------------------


@dataclass
class SubAgentDef:
    description: str
    system_prompt: str
    tools: list[dict]
    model: str = SONNET
    max_tokens: int = 2048
    max_iterations: int = 6


SUBAGENTS: dict[str, SubAgentDef] = {
    "strategy-advisor": SubAgentDef(
        description="Trading strategy specialist. Discusses, structures, and saves strategies to DB.",  # noqa: E501
        system_prompt=STRATEGY_ADVISOR_PROMPT,
        tools=[*STRATEGY_TOOLS, WEB_SEARCH_TOOL],
        model=SONNET,
        max_tokens=2048,
        max_iterations=6,
    ),
    "trade-executor": SubAgentDef(
        description="Automated trade executor. Checks strategy conditions and places KIS orders (KR/US stocks).",  # noqa: E501
        system_prompt=TRADE_EXECUTOR_PROMPT,
        tools=[*TRADE_TOOLS, WEB_SEARCH_TOOL],
        model=HAIKU,  # Haiku: rule-based execution, no complex reasoning needed
        max_tokens=1024,
        max_iterations=6,
    ),
}

# Task tool schema for orchestrator
TASK_TOOL = {
    "name": "task",
    "description": (
        "Delegate a task to a specialized sub-agent. "
        "Available agents: " + ", ".join(f'"{k}": {v.description}' for k, v in SUBAGENTS.items())
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": list(SUBAGENTS.keys()),
                "description": "Which sub-agent to invoke",
            },
            "task": {
                "type": "string",
                "description": "Full task description including relevant context",
            },
        },
        "required": ["agent", "task"],
    },
}

ORCHESTRATOR_TOOLS = [*PORTFOLIO_TOOLS, WEB_SEARCH_TOOL, TASK_TOOL]


# ---------------------------------------------------------------------------
# Core agentic loop
# ---------------------------------------------------------------------------


def _build_client() -> anthropic.Anthropic:
    from app.infrastructure.config import get_settings

    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise ValueError(
            "Anthropic API 키가 설정되지 않았습니다. Settings 페이지에서 입력해 주세요."
        )
    return anthropic.Anthropic(api_key=api_key)


def _tool_status(tool_name: str, tool_input: dict) -> str:
    """Return a Korean status message describing the tool being called."""
    if tool_name == "task":
        agent = tool_input.get("agent", "")
        if agent == "strategy-advisor":
            return "전략 어드바이저 에이전트 실행 중..."
        elif agent == "trade-executor":
            return "거래 실행 에이전트 실행 중..."
        return f"{agent} 에이전트 실행 중..."
    status_map = {
        "web_search": "웹 검색 중...",
        "get_portfolio": "포트폴리오 데이터 조회 중...",
        "get_strategies": "전략 목록 조회 중...",
        "evaluate_strategy": "전략 조건 평가 중...",
        "place_order": "주문 실행 중...",
        "save_strategy": "전략 저장 중...",
        "get_broker_account": "계좌 정보 조회 중...",
        "check_dca_due": "DCA 일정 확인 중...",
        "get_scheduler_runs": "스케줄러 이력 조회 중...",
    }
    return status_map.get(tool_name, f"{tool_name} 실행 중...")


def run_agent(
    system_prompt: str,
    tools: list[dict],
    messages: list[dict],
    model: str = SONNET,
    max_tokens: int = 2048,
    max_iterations: int = 5,
) -> Generator[dict, None, None]:
    """
    Run an agentic loop, yielding dicts as they arrive:
      {"type": "content", "text": str}  — text token
      {"type": "status",  "text": str}  — tool call progress message
    System prompt and tool schemas are sent with cache_control to reduce
    repeated input token costs.
    """
    client = _build_client()
    loop_messages = list(messages)
    cached_system = _cached_system(system_prompt)
    cached_tools = _cached_tools(tools)

    for _ in range(max_iterations):
        response = _api_create_with_retry(
            client,
            model=model,
            max_tokens=max_tokens,
            system=cached_system,
            tools=cached_tools,
            messages=loop_messages,
        )

        text_parts: list[str] = []
        tool_uses: list[Any] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append(block)

        if text_parts:
            yield {"type": "content", "text": "".join(text_parts)}

        if response.stop_reason == "end_turn" or not tool_uses:
            break

        loop_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_uses:
            tool_name = tool_block.name
            tool_input = tool_block.input
            logger.debug(f"tool call: {tool_name}")

            yield {"type": "status", "text": _tool_status(tool_name, tool_input)}

            if tool_name == "task":
                result = yield from _run_subagent_with_keepalive(
                    tool_input["agent"], tool_input["task"]
                )
            else:
                result = dispatch_tool(tool_name, tool_input)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(result, default=str),
                }
            )

        loop_messages.append({"role": "user", "content": tool_results})


def _run_subagent_with_keepalive(
    agent_name: str, task: str
) -> Generator[dict, None, dict]:
    """Run subagent in a background thread, yielding keepalive events every 5 s.

    Use as: ``result = yield from _run_subagent_with_keepalive(name, task)``

    PEP 380: the generator's ``return`` value becomes the value of the
    ``yield from`` expression in the caller, so the caller receives the
    subagent result without any extra plumbing.
    """
    rq: _queue.Queue = _queue.Queue()

    def _bg() -> None:
        try:
            rq.put(("ok", _run_subagent(agent_name, task)))
        except Exception as exc:  # noqa: BLE001
            rq.put(("err", exc))

    threading.Thread(target=_bg, daemon=True).start()

    while True:
        try:
            kind, val = rq.get(timeout=5.0)
            if kind == "err":
                raise val  # type: ignore[misc]
            return val  # type: ignore[return-value]  # PEP 380 generator return
        except _queue.Empty:
            yield {"type": "keepalive"}


def _run_subagent(agent_name: str, task: str) -> dict:
    """Run a sub-agent synchronously and return its final response.

    Uses per-agent model, max_tokens, and max_iterations from SubAgentDef.
    System prompt and tools are cached to reduce input token costs.
    """
    defn = SUBAGENTS.get(agent_name)
    if defn is None:
        return {"error": f"Unknown sub-agent: {agent_name}"}

    logger.info(f"subagent '{agent_name}' started")

    try:
        client = _build_client()
        messages = [{"role": "user", "content": task}]
        cached_system = _cached_system(defn.system_prompt)
        cached_tools = _cached_tools(defn.tools)

        text_parts: list[str] = []

        for _iteration in range(defn.max_iterations):
            response = _api_create_with_retry(
                client,
                model=defn.model,
                max_tokens=defn.max_tokens,
                system=cached_system,
                tools=cached_tools,
                messages=messages,
            )

            text_parts = []
            tool_uses = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason == "end_turn" or not tool_uses:
                logger.info(f"subagent '{agent_name}' completed")
                return {"result": "".join(text_parts)}

            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tb in tool_uses:
                logger.debug(f"tool call: {tb.name}")
                result = dispatch_tool(tb.name, tb.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tb.id,
                        "content": json.dumps(result, default=str),
                    }
                )

            messages.append({"role": "user", "content": tool_results})

        logger.warning(f"subagent '{agent_name}' reached max_iterations")
        return {"result": "".join(text_parts) if text_parts else "Sub-agent completed."}
    except Exception as e:
        logger.error(f"subagent '{agent_name}' failed: {e}")
        return {"error": f"Sub-agent '{agent_name}' failed: {e}"}


# ---------------------------------------------------------------------------
# Streaming orchestrator (for Streamlit chat)
# ---------------------------------------------------------------------------


def stream_orchestrator(
    user_message: str,
    history: list[dict],
) -> Generator[dict, None, None]:
    """
    Stream orchestrator response for a new user message.
    history: list of {"role": "user"|"assistant", "content": str}
    """
    messages = [
        *history[-_HISTORY_LIMIT:],
        {"role": "user", "content": user_message},
    ]
    yield from run_agent(
        system_prompt=ORCHESTRATOR_PROMPT,
        tools=ORCHESTRATOR_TOOLS,
        messages=messages,
        model=SONNET,
        max_tokens=2048,
        max_iterations=5,
    )


def run_trade_executor(markets_open: list[str] | None = None) -> str:
    """
    Run the trade executor sub-agent once (for scheduled/manual trigger).
    Returns the agent's summary.

    Args:
        markets_open: 현재 열린 시장 목록 (e.g. ['KR'], ['US'], ['KR', 'US']).
                      None이면 에이전트가 현재 시각으로 판단.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    now_et = datetime.now(ZoneInfo("America/New_York"))
    kst_str = now_kst.strftime("%Y-%m-%d %H:%M KST (%A)")
    et_str = now_et.strftime("%H:%M ET")

    if markets_open is not None:
        market_info = (
            f"Currently open markets: {', '.join(markets_open) if markets_open else 'none'}. "
        )
        market_info += "Only evaluate and execute strategies for these markets. "
    else:
        market_info = "KR strategies trade KST 09:00-15:30, US strategies trade ET 09:30-16:00. "

    task = (
        f"Current time: {kst_str} / {et_str}\n\n"
        "Review all active strategies, check current market conditions, "
        "and execute any triggered orders. " + market_info
    )

    logger.info("run_trade_executor started")
    result = _run_subagent("trade-executor", task)
    logger.info("run_trade_executor completed")
    return result.get("result", "Trade executor completed.")
