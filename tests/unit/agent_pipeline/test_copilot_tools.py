"""Tests for AGENT-04: Copilot tool functions return valid JSON-serializable dicts."""
import json
from unittest.mock import patch, MagicMock

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
    scan_top_pm_edges,
    check_pm_correlation,
    search_games,
    resolve_game,
    compare_books,
    get_model_predictions,
)


def _stub_pending_bets(*args, **kwargs):
    """Stub returning empty pending bets list (no DB call)."""
    return []


def _stub_performance_summary(*args, **kwargs):
    """Stub returning minimal PerformanceSummary-like object."""
    m = MagicMock()
    m.total_bets = 0
    m.wins = 0
    m.losses = 0
    m.win_rate = 0.0
    m.roi = 0.0
    m.units_won = 0.0
    return m


def _stub_value_plays(*args, **kwargs):
    return []


def _stub_line_movements(*args, **kwargs):
    return []


def _stub_movement_summary(*args, **kwargs):
    return {"steam_moves": 0, "rlm_moves": 0, "significant_movements": 0}


def _stub_projection(*args, **kwargs):
    return None


TOOLS = [
    ("get_active_bets", get_active_bets, {}),
    ("get_portfolio_stats", get_portfolio_stats, {}),
    ("analyze_game", analyze_game, {"game_query": "Lakers vs Celtics"}),
    ("search_value_plays", search_value_plays, {"sport": "NBA"}),
    ("check_line_movement", check_line_movement, {"game_id": "game-123"}),
    ("get_sharp_indicators", get_sharp_indicators, {"game_id": "game-123"}),
    ("estimate_bankroll_risk", estimate_bankroll_risk, {"stake": 100, "odds": -110}),
    ("get_prediction_market_edge", get_prediction_market_edge, {"market_id": "pm-456"}),
    ("scan_top_pm_edges", scan_top_pm_edges, {}),
    ("check_pm_correlation", check_pm_correlation, {"pm_market_title": "Will Team A win?"}),
    ("search_games", search_games, {"sport": "NBA", "query": ""}),
    ("resolve_game", resolve_game, {"sport": "NBA", "query": "Lakers"}),
    ("compare_books", compare_books, {"game_id": "game-123", "sport": "NBA"}),
    ("get_model_predictions", get_model_predictions, {"game_id": "game-123"}),
]


@pytest.mark.parametrize("name,tool_fn,kwargs", TOOLS, ids=[t[0] for t in TOOLS])
def test_all_copilot_tools_return_valid_json(name, tool_fn, kwargs):
    """Each tool function returns a dict that is JSON-serializable.

    Tools are LangChain StructuredTool objects; invoke() is used to call them.
    """
    patches = [
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_pending_bets",
            side_effect=_stub_pending_bets,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_performance_summary",
            side_effect=_stub_performance_summary,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_active_value_plays",
            side_effect=_stub_value_plays,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_line_movements",
            side_effect=_stub_line_movements,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_movement_summary",
            side_effect=_stub_movement_summary,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.get_projection",
            side_effect=_stub_projection,
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.search_games_impl",
            return_value={"games": [], "count": 0},
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.resolve_game_impl",
            return_value={"game": None, "candidates": [], "error": "stub"},
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.run_compare_books",
            return_value={"game_id": "game-123", "books": []},
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.scan_top_pm_edges_impl",
            return_value={"edges": [], "count": 0},
        ),
        patch(
            "sharpedge_agent_pipeline.copilot.tools.check_pm_correlation_impl",
            return_value={"correlation": None, "warnings": [], "count": 0},
        ),
    ]

    with (
        patches[0],
        patches[1],
        patches[2],
        patches[3],
        patches[4],
        patches[5],
        patches[6],
        patches[7],
        patches[8],
        patches[9],
        patches[10],
    ):
        # StructuredTool.invoke(dict) is the correct way to call a @tool function
        result = tool_fn.invoke(kwargs)

    # Must be serializable to JSON
    serialized = json.dumps(result)
    assert serialized is not None
    parsed = json.loads(serialized)
    assert isinstance(parsed, (dict, list))
