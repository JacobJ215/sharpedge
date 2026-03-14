"""BettingCopilot — ReAct-style LangGraph StateGraph.

Separate from the 9-node analysis graph (graph.py). This graph provides
a conversational assistant that can call any of the 10 copilot tools.

Build once at module import via the COPILOT_GRAPH singleton.

Usage:
    result = COPILOT_GRAPH.invoke({"messages": [{"role": "user", "content": "..."}]})
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode

from sharpedge_agent_pipeline.copilot.session import trim_conversation
from sharpedge_agent_pipeline.copilot.tools import (
    COPILOT_TOOLS,
    get_active_bets,         # exposed for monkeypatching in tests
    get_portfolio_stats,
    analyze_game,
    search_value_plays,
    check_line_movement,
    get_sharp_indicators,
    estimate_bankroll_risk,
    get_prediction_market_edge,
    compare_books,
    get_model_predictions,
)


def build_copilot_graph(tools: list | None = None) -> object:
    """Build and compile the BettingCopilot ReAct StateGraph.

    Uses MessagesState + ToolNode pattern. The agent node trims the conversation
    before every LLM call to keep within the GPT-4o context window.

    Args:
        tools: List of @tool functions to bind. Defaults to all 10 COPILOT_TOOLS.

    Returns:
        Compiled LangGraph StateGraph.
    """
    if tools is None:
        tools = COPILOT_TOOLS

    llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools(tools)
    tool_node = ToolNode(tools)

    def agent_node(state: MessagesState) -> dict:
        """Trim conversation history then invoke the LLM."""
        # MessagesState stores messages as BaseMessage objects or dicts
        messages = state["messages"]
        # Convert to plain dicts for trim_conversation compatibility
        plain = [
            m if isinstance(m, dict) else {"role": _role(m), "content": str(getattr(m, "content", ""))}
            for m in messages
        ]
        trimmed_dicts = trim_conversation(plain)
        # Re-map trimmed indices back to original BaseMessage objects for LLM
        kept_count = len(trimmed_dicts)
        trimmed_msgs = messages[-kept_count:] if kept_count < len(messages) else messages
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
    return g.compile()


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
        return build_copilot_graph(tools=COPILOT_TOOLS)
    except Exception:  # pragma: no cover
        return None


# Module-level singleton — None when OPENAI_API_KEY is not set
COPILOT_GRAPH = _try_build_graph()
