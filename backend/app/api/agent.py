"""Agent API — SSE chat stream, trade executor trigger."""

import json
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.application.agent import run_trade_executor, stream_orchestrator

router = APIRouter(dependencies=[Depends(get_current_user)])


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[HistoryMessage] = Field(default_factory=list)


@router.post("/agent/chat/stream")
def chat_stream(req: ChatRequest):
    """오케스트레이터 에이전트 응답을 SSE로 스트리밍."""

    def generate():
        try:
            history_dicts = [m.model_dump() for m in req.history]
            for chunk in stream_orchestrator(req.message, history_dicts):
                if chunk.get("type") == "status":
                    yield f"data: {json.dumps({'status': chunk['text']})}\n\n"
                else:
                    yield f"data: {json.dumps({'content': chunk['text']})}\n\n"
        except Exception as e:
            logger.error(f"stream_orchestrator error: {e}")
            yield f"data: {json.dumps({'error': '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'})}\n\n"  # noqa: E501
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/agent/trade-executor")
def trigger_trade_executor():
    """Trade Executor 수동 실행."""
    try:
        result = run_trade_executor()
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
