"""GREEN verification test for WIRE-06: BettingCopilot has exactly 12 tools.

WIRE-06: COPILOT_TOOLS list must contain exactly 12 entries.

This is a GREEN test — COPILOT_TOOLS already has 10 base tools + 2 VENUE_TOOLS = 12.
"""

from __future__ import annotations


def test_copilot_tools_has_12_entries() -> None:
    """COPILOT_TOOLS list contains exactly 12 tool entries.

    GREEN: tools.py assembles 10 base tools + VENUE_TOOLS (get_venue_dislocation,
    get_exposure_status) = 12 total.
    """
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    assert len(COPILOT_TOOLS) == 12, (
        f"Expected 12 copilot tools, got {len(COPILOT_TOOLS)}. "
        f"Tools: {[t.name for t in COPILOT_TOOLS]}"
    )


def test_copilot_tools_includes_venue_tools() -> None:
    """COPILOT_TOOLS includes the two venue tools: get_venue_dislocation and get_exposure_status.

    GREEN: VENUE_TOOLS are appended via list concatenation in tools.py.
    """
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    tool_names = [t.name for t in COPILOT_TOOLS]
    assert "get_venue_dislocation" in tool_names, (
        f"get_venue_dislocation missing from COPILOT_TOOLS. Got: {tool_names}"
    )
    assert "get_exposure_status" in tool_names, (
        f"get_exposure_status missing from COPILOT_TOOLS. Got: {tool_names}"
    )


def test_copilot_tools_includes_base_tools() -> None:
    """COPILOT_TOOLS includes the 10 base tools.

    GREEN: base tools defined in COPILOT_TOOLS list in tools.py.
    """
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    expected_base_tools = [
        "get_active_bets",
        "get_portfolio_stats",
        "analyze_game",
        "search_value_plays",
        "check_line_movement",
        "get_sharp_indicators",
        "estimate_bankroll_risk",
        "get_prediction_market_edge",
        "compare_books",
        "get_model_predictions",
    ]
    tool_names = [t.name for t in COPILOT_TOOLS]
    for tool_name in expected_base_tools:
        assert tool_name in tool_names, (
            f"Base tool '{tool_name}' missing from COPILOT_TOOLS. Got: {tool_names}"
        )
