"""POST /api/v1/copilot/chat — BettingCopilot SSE streaming."""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["v1"])

# LangGraph astream_events(..., version="v1") — exact event keys observed for copilot (see
# .planning/phases/copilot-commercial-04/04-RESEARCH.md §1):
#   - on_chat_model_stream — assistant token chunks (user-visible prose)
#   - on_tool_start — tool invocation begins (emit copilot_tool phase=start)
#   - on_tool_end — tool invocation completes (emit copilot_tool phase=end; do not forward raw output)

_INPUT_SUMMARY_KEYS = frozenset(
    {
        "sport",
        "game_id",
        "game_query",
        "market_id",
        "limit",
        "offset",
        "max_results",
        "top_n",
    }
)


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


def _summarize_tool_input(name: str, inp: object) -> str:
    """Single-line summary from tool name + allowlisted args (max 120 chars). Omits user_id and unknown keys."""
    if not isinstance(inp, dict):
        base = name.strip() or "tool"
        return base[:120]

    parts: list[str] = []
    for key in sorted(inp.keys()):
        if key == "user_id":
            continue
        if key not in _INPUT_SUMMARY_KEYS:
            continue
        val = inp[key]
        if val is None:
            continue
        vs = str(val).replace("\n", " ").strip()
        if len(vs) > 48:
            vs = vs[:45] + "…"
        parts.append(f"{key}={vs}")

    suffix = (" " + " ".join(parts)) if parts else ""
    raw = f"{name}{suffix}".strip() or name
    raw = re.sub(r"\s+", " ", raw)
    return raw[:120]


def _summarize_tool_end(name: str, output: object) -> str:
    """Safe end summary — never forward full tool output."""
    if output is None:
        return "done"
    if isinstance(output, dict) and "count" in output:
        c = output["count"]
        if isinstance(c, (int, float)):
            return f"count={int(c)}"
    text = output if isinstance(output, str) else str(output)
    text = text.strip()
    if not text:
        return "done"
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "count" in parsed:
            c = parsed["count"]
            if isinstance(c, (int, float)):
                return f"count={int(c)}"
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return "done"


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
    """Yield SSE records: assistant text as event:message; tool trace as event:copilot_tool; terminator data:[DONE]."""
    if graph is None:
        yield "event: message\ndata: BettingCopilot is not configured (missing OPENAI_API_KEY)\n\n"
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
            ev_name = event.get("event")
            if ev_name == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    safe_content = chunk.content.replace("\n", "\\n")
                    yield f"event: message\ndata: {safe_content}\n\n"
            elif ev_name == "on_tool_start":
                tool_name = str(event.get("name") or "tool")
                raw_inp = event.get("data", {}).get("input")
                summary = _summarize_tool_input(tool_name, raw_inp)
                payload = json.dumps(
                    {"phase": "start", "name": tool_name, "summary": summary},
                    ensure_ascii=False,
                )
                yield f"event: copilot_tool\ndata: {payload}\n\n"
            elif ev_name == "on_tool_end":
                tool_name = str(event.get("name") or "tool")
                out = event.get("data", {}).get("output")
                summary = _summarize_tool_end(tool_name, out)
                payload = json.dumps(
                    {"phase": "end", "name": tool_name, "summary": summary},
                    ensure_ascii=False,
                )
                yield f"event: copilot_tool\ndata: {payload}\n\n"
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
