"""Tests for AGENT-03: BettingCopilot active bets awareness via mocked tools."""
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_agent_pipeline.copilot.agent import build_copilot_graph


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
def test_active_bets_awareness():
    """Copilot response string contains bet game names from mocked get_active_bets."""
    mock_bets = [
        {"game": "Lakers vs Celtics", "side": "Lakers ML", "stake": 100},
        {"game": "Chiefs vs Eagles", "side": "Chiefs -3", "stake": 150},
    ]

    with patch("sharpedge_agent_pipeline.copilot.agent.get_active_bets", return_value=mock_bets):
        graph = build_copilot_graph()
        result = graph.invoke(
            {"messages": [{"role": "user", "content": "What bets do I have active?"}]}
        )
        # Final message content must mention the game names
        final_content = result["messages"][-1].content
        assert "Lakers vs Celtics" in final_content or "Chiefs vs Eagles" in final_content
