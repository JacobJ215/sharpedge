"""POST /api/v1/copilot/chat — BettingCopilot SSE streaming."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

router = APIRouter(tags=["v1"])


class CopilotRequest(BaseModel):
    message: str
    session_id: str | None = None


def build_copilot_graph():
    """Lazy wrapper to build copilot graph. Returns None if unavailable."""
    try:
        from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph as _build

        return _build()
    except Exception:
        return None


def _resolve_user_id(token: str) -> str | None:
    """Resolve user_id from a Supabase JWT. Returns None if invalid or env unconfigured."""
    try:
        from supabase import create_client  # lazy import

        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        if not url or not key:
            return None
        client = create_client(url, key)
        result = client.auth.get_user(token)
        if result and result.user:
            return result.user.id
        return None
    except Exception:
        return None


async def _stream_copilot(message: str, user_id: str | None = None) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted tokens from BettingCopilot graph."""
    graph = build_copilot_graph()

    if graph is None:
        # Graceful degradation when OPENAI_API_KEY absent
        yield "data: BettingCopilot is not configured (missing OPENAI_API_KEY)\n\n"
        yield "data: [DONE]\n\n"
        return

    input_state = {"messages": [{"role": "user", "content": message}]}
    run_config: dict = {"configurable": {"user_id": user_id}}

    try:
        async for event in graph.astream_events(input_state, config=run_config, version="v1"):
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
async def copilot_chat(
    request: CopilotRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> StreamingResponse:
    """Stream BettingCopilot response as Server-Sent Events. Optional auth — degrades gracefully."""
    user_id: str | None = None
    if authorization:
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            user_id = _resolve_user_id(token)

    return StreamingResponse(
        _stream_copilot(request.message, user_id=user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
