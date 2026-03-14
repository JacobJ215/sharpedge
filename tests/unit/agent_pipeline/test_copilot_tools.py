"""Tests for AGENT-04: Copilot tool functions return valid JSON-serializable dicts."""
import json

import pytest

from sharpedge_agent_pipeline.copilot.tools import (
    get_active_bets,
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

TOOLS = [
    ("get_active_bets", get_active_bets, {}),
    ("get_portfolio_stats", get_portfolio_stats, {}),
    ("analyze_game", analyze_game, {"game_query": "Lakers vs Celtics"}),
    ("search_value_plays", search_value_plays, {"sport": "NBA"}),
    ("check_line_movement", check_line_movement, {"game_id": "game-123"}),
    ("get_sharp_indicators", get_sharp_indicators, {"game_id": "game-123"}),
    ("estimate_bankroll_risk", estimate_bankroll_risk, {"stake": 100, "odds": -110}),
    ("get_prediction_market_edge", get_prediction_market_edge, {"market_id": "pm-456"}),
    ("compare_books", compare_books, {"game_id": "game-123"}),
    ("get_model_predictions", get_model_predictions, {"game_id": "game-123"}),
]


@pytest.mark.xfail(strict=True, reason="Wave 1 not yet implemented")
@pytest.mark.parametrize("name,tool_fn,kwargs", TOOLS, ids=[t[0] for t in TOOLS])
def test_all_10_tools_return_valid_json(name, tool_fn, kwargs):
    """Each tool function returns a dict that is JSON-serializable."""
    result = tool_fn(**kwargs)
    # Must be serializable to JSON
    serialized = json.dumps(result)
    assert serialized is not None
    parsed = json.loads(serialized)
    assert isinstance(parsed, (dict, list))
