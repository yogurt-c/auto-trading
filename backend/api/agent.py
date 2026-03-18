"""Agent API — SSE chat stream, trade executor trigger."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from application.agent import run_trade_executor, stream_orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list = []


@router.post("/agent/chat/stream")
def chat_stream(req: ChatRequest):
    """오케스트레이터 에이전트 응답을 SSE로 스트리밍."""

    def generate():
        try:
            for chunk in stream_orchestrator(req.message, req.history):
                if chunk.get("type") == "status":
                    yield f"data: {json.dumps({'status': chunk['text']})}\n\n"
                else:
                    yield f"data: {json.dumps({'content': chunk['text']})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
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
