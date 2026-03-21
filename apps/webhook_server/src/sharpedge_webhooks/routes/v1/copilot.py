"""POST /api/v1/copilot/chat — BettingCopilot SSE streaming."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["v1"])


class CopilotRequest(BaseModel):
    message: str
    thread_id: str | None = Field(
        default=None,
        description="Client-owned conversation id for LangGraph checkpointing when enabled.",
    )
    session_id: str | None = Field(
        default=None,
        description="Deprecated alias for thread_id.",
    )


def build_copilot_graph():
    """Lazy wrapper to build copilot graph without server checkpointer. Returns None if unavailable."""
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


def _copilot_persist_active(request: Request) -> bool:
    """True when Postgres checkpointer is active (requires thread_id per request)."""
    persist = bool(getattr(request.app.state, "copilot_persist_threads", False))
    state_graph = getattr(request.app.state, "copilot_graph", None)
    return persist and state_graph is not None


def _resolve_graph(request: Request):
    """Prefer graph compiled with checkpointer from lifespan; else ephemeral graph."""
    g = getattr(request.app.state, "copilot_graph", None)
    if g is not None:
        return g
    return build_copilot_graph()


async def _stream_copilot(
    graph: object,
    message: str,
    *,
    user_id: str | None,
    run_config: dict,
) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted tokens from BettingCopilot graph."""
    if graph is None:
        yield "data: BettingCopilot is not configured (missing OPENAI_API_KEY)\n\n"
        yield "data: [DONE]\n\n"
        return

    try:
        from langchain_core.messages import HumanMessage
    except ImportError:
        yield "data: {\"error\": \"langchain_core not available\"}\n\n"
        yield "data: [DONE]\n\n"
        return

    input_state = {"messages": [HumanMessage(content=message)]}

    try:
        async for event in graph.astream_events(input_state, config=run_config, version="v1"):
            if event.get("event") == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    safe_content = chunk.content.replace("\n", "\\n")
                    yield f"data: {safe_content}\n\n"
    except Exception as exc:
        error_msg = json.dumps({"error": str(exc)})
        yield f"data: {error_msg}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/copilot/chat")
async def copilot_chat(
    request: Request,
    body: CopilotRequest,
    authorization: str | None = Header(None, alias="Authorization"),
) -> StreamingResponse:
    """Stream BettingCopilot response as Server-Sent Events. Optional auth — degrades gracefully."""
    user_id: str | None = None
    if authorization:
        token = authorization.removeprefix("Bearer ").strip()
        if token:
            user_id = _resolve_user_id(token)

    graph = _resolve_graph(request)
    persist = _copilot_persist_active(request)
    client_thread = (body.thread_id or body.session_id or "").strip()
    if persist and not client_thread:
        raise HTTPException(
            status_code=400,
            detail="thread_id is required when conversation persistence is enabled",
        )

    run_config: dict = {"configurable": {"user_id": user_id}}
    if persist and client_thread:
        run_config["configurable"]["thread_id"] = f"{user_id or 'anon'}:{client_thread}"

    return StreamingResponse(
        _stream_copilot(graph, body.message, user_id=user_id, run_config=run_config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
