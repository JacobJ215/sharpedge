"""BettingCopilot — ReAct-style LangGraph StateGraph.

Separate from the 9-node analysis graph (graph.py). This graph provides
a conversational assistant that calls copilot tools (see ``COPILOT_TOOLS``).

When ``build_copilot_graph()`` is called with ``tools=None`` (default), the
router applies ``COPILOT_ROUTER_FOCUS`` (``all`` | ``sports`` | ``pm`` |
``portfolio``) — see :mod:`sharpedge_agent_pipeline.copilot.router`.

Build once at module import via the COPILOT_GRAPH singleton.

Usage:
    result = COPILOT_GRAPH.invoke({"messages": [{"role": "user", "content": "..."}]})
"""

from __future__ import annotations

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from sharpedge_agent_pipeline.copilot.prompts import COPILOT_SYSTEM_PROMPT
from sharpedge_agent_pipeline.copilot.router import resolve_tool_subset
from sharpedge_agent_pipeline.copilot.session import trim_conversation
from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS


def build_copilot_graph(
    tools: list | None = None,
    checkpointer: object | None = None,
) -> object:
    """Build and compile the BettingCopilot ReAct StateGraph.

    Uses MessagesState + ToolNode pattern. The agent node trims the conversation
    before every LLM call to keep within the GPT-4o context window.

    Args:
        tools: List of @tool functions to bind. When ``None``, uses
            :func:`~sharpedge_agent_pipeline.copilot.router.resolve_tool_subset`
            (reads ``COPILOT_ROUTER_FOCUS``). Passing an explicit list skips the
            router and uses no focus addendum.
        checkpointer: Optional LangGraph checkpointer (e.g. AsyncPostgresSaver) for threads.

    Returns:
        Compiled LangGraph StateGraph.
    """
    system_addendum = ""
    if tools is None:
        tools, system_addendum = resolve_tool_subset()
    else:
        tools = list(tools)

    llm = ChatOpenAI(model="gpt-5.4-mini-2026-03-17", temperature=0).bind_tools(tools)
    tool_node = ToolNode(tools)

    def agent_node(state: MessagesState) -> dict:
        """Trim conversation history then invoke the LLM."""
        # MessagesState stores messages as BaseMessage objects or dicts
        messages = state["messages"]
        # Convert to plain dicts for trim_conversation compatibility
        plain = [
            m
            if isinstance(m, dict)
            else {"role": _role(m), "content": str(getattr(m, "content", ""))}
            for m in messages
        ]
        trimmed_dicts = trim_conversation(plain)
        # Re-map trimmed indices back to original BaseMessage objects for LLM
        kept_count = len(trimmed_dicts)
        trimmed_msgs = messages[-kept_count:] if kept_count < len(messages) else messages
        trimmed_msgs = _with_system_prompt(trimmed_msgs, system_addendum=system_addendum)
        response = llm.invoke(trimmed_msgs)
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> str:
        """Route to tools node or END based on whether last message has tool calls."""
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None)
        if tool_calls:
            return "tools"
        return END

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tool_node)
    g.set_entry_point("agent")
    g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    g.add_edge("tools", "agent")
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def _with_system_prompt(msgs: list, *, system_addendum: str = "") -> list:
    """Prepend canonical system prompt; drop prior system messages to avoid drift."""
    out: list = []
    for m in msgs:
        if isinstance(m, BaseMessage) and m.type == "system":
            continue
        if isinstance(m, dict) and m.get("role") == "system":
            continue
        out.append(m)
    body = COPILOT_SYSTEM_PROMPT
    extra = (system_addendum or "").strip()
    if extra:
        body = f"{body}\n\n---\n{extra}"
    return [SystemMessage(content=body), *out]


def _role(msg: object) -> str:
    """Extract role string from a BaseMessage or similar object."""
    msg_type = type(msg).__name__.lower()
    if "human" in msg_type:
        return "user"
    if "ai" in msg_type or "assistant" in msg_type:
        return "assistant"
    if "system" in msg_type:
        return "system"
    if "tool" in msg_type:
        return "tool"
    return "user"


def _try_build_graph() -> object | None:
    """Build the COPILOT_GRAPH singleton at import time if OPENAI_API_KEY is set.

    Returns None in environments without the API key (e.g., test/offline).
    Use build_copilot_graph() directly when you need an explicit graph instance.
    """
    import os

    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        return build_copilot_graph()
    except Exception:  # pragma: no cover
        return None


# Module-level singleton — None when OPENAI_API_KEY is not set
COPILOT_GRAPH = _try_build_graph()
