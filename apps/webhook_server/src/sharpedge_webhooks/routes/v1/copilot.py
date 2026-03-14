"""POST /api/v1/copilot/chat — BettingCopilot SSE streaming."""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(tags=["v1"])


class CopilotRequest(BaseModel):
    message: str
    session_id: str | None = None


def build_copilot_graph():
    """Lazy wrapper to build copilot graph. Returns None if unavailable."""
    try:
        from sharpedge_bot.copilot_graph import build_copilot_graph as _build
        return _build()
    except Exception:
        return None


async def _stream_copilot(message: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted tokens from BettingCopilot graph."""
    graph = build_copilot_graph()

    if graph is None:
        # Graceful degradation when OPENAI_API_KEY absent
        yield "data: BettingCopilot is not configured (missing OPENAI_API_KEY)\n\n"
        yield "data: [DONE]\n\n"
        return

    input_state = {"messages": [{"role": "user", "content": message}]}

    try:
        async for event in graph.astream_events(input_state, version="v1"):
            if event.get("event") == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Escape newlines within content so SSE format is preserved
                    safe_content = chunk.content.replace("\n", "\\n")
                    yield f"data: {safe_content}\n\n"
    except Exception as exc:
        error_msg = json.dumps({"error": str(exc)})
        yield f"data: {error_msg}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/copilot/chat")
async def copilot_chat(request: CopilotRequest) -> StreamingResponse:
    """Stream BettingCopilot response as Server-Sent Events. Public endpoint."""
    return StreamingResponse(
        _stream_copilot(request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
