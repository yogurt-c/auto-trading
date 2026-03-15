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
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Generator

import anthropic
from loguru import logger

from .tools import (
    PORTFOLIO_TOOLS,
    STRATEGY_TOOLS,
    TRADE_TOOLS,
    WEB_SEARCH_TOOL,
    dispatch_tool,
)

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

ORCHESTRATOR_PROMPT = """\
You are a professional portfolio manager assistant.
You help users understand their portfolio performance, analyze holdings, and answer market questions.

You have access to:
- get_portfolio: retrieve current holdings
- web_search: look up current prices, news, and market data
- task: delegate complex sub-tasks to specialized agents

When the user wants to create or manage a trading strategy, delegate to the "strategy-advisor" sub-agent.
When the user asks to execute trades or check automated trading, delegate to the "trade-executor" sub-agent.

Always be concise, data-driven, and mention specific numbers when analyzing the portfolio.
When citing prices or news, use web_search to get current data.

Response format:
- Use clean markdown only (headers, bold, tables, bullet lists)
- Do not use any emoji or icons in your responses
"""

STRATEGY_ADVISOR_PROMPT = """\
You are a trading strategy advisor specialized in US equities and ETFs.
Your goal is to help users build concrete, executable trading strategies.

Workflow:
1. Discuss the strategy with the user (entry conditions, exit conditions, position sizing)
2. Use web_search to research the ticker if needed
3. Summarize the agreed strategy clearly
4. Call save_strategy to persist the structured parameters
5. If the response contains warnings, explain each one to the user and ask if they want to adjust
6. Confirm the strategy was saved and show the key parameters

Always extract these structured fields when possible:
- entry_price_drop_pct (e.g., buy on -5% dip)
- take_profit_pct / stop_loss_pct
- dca_amount_usd + dca_frequency_days for DCA strategies
- max_position_usd to cap total exposure

Be proactive about risk management: always recommend a stop-loss.

Response format:
- Use clean markdown only (headers, bold, tables, bullet lists)
- Do not use any emoji or icons in your responses
"""

TRADE_EXECUTOR_PROMPT = """\
You are an automated trade execution agent for paper trading.
Your job is to review active strategies and execute orders when conditions are met.

Workflow:
1. Call get_scheduler_runs(limit=10) to review recent execution history
   - Check if previous runs successfully executed planned strategies
   - Identify any patterns of missed signals or repeated failures
2. Call get_strategies(status='active') to get all active strategies
3. Call get_alpaca_account() to check current positions and buying power
4. For each strategy, call evaluate_strategy(strategy_id) to check conditions
   - For DCA strategies: also call check_dca_due(strategy_id); only proceed if is_due is true
   - Do NOT use web_search to manually fetch prices or compute conditions
5. If evaluate_strategy returns entry_triggered=true or exit_triggered=true, call place_order
   - Always pass max_position_usd from the strategy if it is set
6. In your summary, mention: which strategies were checked, what conditions
   were evaluated, which orders were placed, and any concerns about strategy
   execution consistency based on historical runs.

Rules:
- NEVER exceed max_position_usd per strategy
- Always include ai_reasoning explaining why the order was triggered
- If conditions are ambiguous, err on the side of NOT trading
- Only trade during market hours (NYSE: 9:30am-4pm ET)

Response format:
- Use clean markdown only (headers, bold, tables, bullet lists)
- Do not use any emoji or icons in your responses
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
        description="Trading strategy specialist. Discusses, structures, and saves strategies to DB.",
        system_prompt=STRATEGY_ADVISOR_PROMPT,
        tools=[*STRATEGY_TOOLS, WEB_SEARCH_TOOL],
        model=SONNET,
        max_tokens=2048,
        max_iterations=6,
    ),
    "trade-executor": SubAgentDef(
        description="Automated trade executor. Checks strategy conditions and places Alpaca orders.",
        system_prompt=TRADE_EXECUTOR_PROMPT,
        tools=[*TRADE_TOOLS, WEB_SEARCH_TOOL],
        model=HAIKU,       # Haiku: rule-based execution, no complex reasoning needed
        max_tokens=1024,
        max_iterations=6,
    ),
}

# Task tool schema for orchestrator
TASK_TOOL = {
    "name": "task",
    "description": (
        "Delegate a task to a specialized sub-agent. "
        "Available agents: "
        + ", ".join(
            f'"{k}": {v.description}'
            for k, v in SUBAGENTS.items()
        )
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
    from .config import get_settings
    api_key = get_settings().anthropic_api_key
    if not api_key:
        raise ValueError("Anthropic API 키가 설정되지 않았습니다. Settings 페이지에서 입력해 주세요.")
    return anthropic.Anthropic(api_key=api_key)


def run_agent(
    system_prompt: str,
    tools: list[dict],
    messages: list[dict],
    model: str = SONNET,
    max_tokens: int = 2048,
    max_iterations: int = 5,
) -> Generator[str, None, None]:
    """
    Run an agentic loop, yielding text chunks as they arrive.
    System prompt and tool schemas are sent with cache_control to reduce
    repeated input token costs.
    """
    client = _build_client()
    loop_messages = list(messages)
    cached_system = _cached_system(system_prompt)
    cached_tools = _cached_tools(tools)

    for _ in range(max_iterations):
        response = client.messages.create(
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
            yield "".join(text_parts)

        if response.stop_reason == "end_turn" or not tool_uses:
            break

        loop_messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_uses:
            tool_name = tool_block.name
            tool_input = tool_block.input
            logger.debug(f"tool call: {tool_name}")

            if tool_name == "task":
                result = _run_subagent(tool_input["agent"], tool_input["task"])
            else:
                result = dispatch_tool(tool_name, tool_input)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result, default=str),
            })

        loop_messages.append({"role": "user", "content": tool_results})


def _run_subagent(agent_name: str, task: str) -> dict:
    """Run a sub-agent synchronously and return its final response.

    Uses per-agent model, max_tokens, and max_iterations from SubAgentDef.
    System prompt and tools are cached to reduce input token costs.
    """
    defn = SUBAGENTS.get(agent_name)
    if defn is None:
        return {"error": f"Unknown sub-agent: {agent_name}"}

    logger.info(f"subagent '{agent_name}' started")

    client = _build_client()
    messages = [{"role": "user", "content": task}]
    cached_system = _cached_system(defn.system_prompt)
    cached_tools = _cached_tools(defn.tools)

    text_parts: list[str] = []

    for iteration in range(defn.max_iterations):
        response = client.messages.create(
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
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tb.id,
                "content": json.dumps(result, default=str),
            })

        messages.append({"role": "user", "content": tool_results})

    logger.warning(f"subagent '{agent_name}' reached max_iterations")
    return {"result": "".join(text_parts) if text_parts else "Sub-agent completed."}


# ---------------------------------------------------------------------------
# Streaming orchestrator (for Streamlit chat)
# ---------------------------------------------------------------------------

def stream_orchestrator(
    user_message: str,
    history: list[dict],
) -> Generator[str, None, None]:
    """
    Stream orchestrator response for a new user message.
    history: list of {"role": "user"|"assistant", "content": str}
    """
    messages = [
        *history,
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


def run_trade_executor() -> str:
    """
    Run the trade executor sub-agent once (for scheduled/manual trigger).
    Returns the agent's summary.
    """
    logger.info("run_trade_executor started")
    result = _run_subagent(
        "trade-executor",
        "Review all active strategies, check current market conditions, and execute any triggered orders.",
    )
    logger.info("run_trade_executor completed")
    return result.get("result", "Trade executor completed.")
