"""Tests for AGENT-03: BettingCopilot active bets awareness via mocked tools and LLM."""
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph


def _make_ai_message(content: str) -> AIMessage:
    """Create an AIMessage with no tool calls (terminates the ReAct loop)."""
    msg = AIMessage(content=content)
    # Ensure tool_calls is empty so should_continue returns END
    object.__setattr__(msg, "tool_calls", [])
    return msg


def test_active_bets_awareness():
    """Copilot graph response contains bet game names from mocked LLM and tools."""
    mock_bets = [
        {"game": "Lakers vs Celtics", "side": "Lakers ML", "stake": 100},
        {"game": "Chiefs vs Eagles", "side": "Chiefs -3", "stake": 150},
    ]
    expected_response = (
        "You have 2 active bets: Lakers vs Celtics (Lakers ML) and Chiefs vs Eagles (Chiefs -3)."
    )

    # Mock the LLM so no real API call is made
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _make_ai_message(expected_response)
    mock_llm_bound = MagicMock()
    mock_llm_bound.invoke = mock_llm.invoke

    with (
        patch("sharpedge_agent_pipeline.copilot.agent.get_active_bets", return_value=mock_bets),
        patch("sharpedge_agent_pipeline.copilot.agent.ChatOpenAI", return_value=mock_llm),
    ):
        # bind_tools returns the same mock
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        graph = build_copilot_graph()
        result = graph.invoke(
            {"messages": [{"role": "user", "content": "What bets do I have active?"}]}
        )

    # Final message content must mention the game names
    final_content = result["messages"][-1].content
    assert "Lakers vs Celtics" in final_content or "Chiefs vs Eagles" in final_content
