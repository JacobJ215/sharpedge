"""COPILOT_TOOLS composition — base + venue dislocation + extended; optional sim exposure."""

from __future__ import annotations

import importlib

import pytest

_EXPECTED_ALWAYS = frozenset(
    {
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
        "get_venue_dislocation",
        "compute_kelly",
        "get_user_exposure",
        "get_injury_report",
    }
)


def test_copilot_tools_default_count_and_names() -> None:
    """Default env: 14 tools; get_exposure_status omitted unless sim flag set at import."""
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    names = [t.name for t in COPILOT_TOOLS]
    assert len(names) == len(_EXPECTED_ALWAYS)
    assert set(names) == _EXPECTED_ALWAYS
    assert "get_exposure_status" not in names


def test_copilot_tools_includes_venue_dislocation() -> None:
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    assert "get_venue_dislocation" in [t.name for t in COPILOT_TOOLS]


def test_copilot_tools_includes_base_tools() -> None:
    from sharpedge_agent_pipeline.copilot.tools import COPILOT_TOOLS

    tool_names = [t.name for t in COPILOT_TOOLS]
    for name in (
        "get_active_bets",
        "get_portfolio_stats",
        "analyze_game",
        "compare_books",
    ):
        assert name in tool_names


@pytest.mark.parametrize("flag", ["1", "true", "yes"])
def test_copilot_tools_includes_exposure_sim_when_env_set(monkeypatch, flag: str) -> None:
    monkeypatch.delenv("COPILOT_VENUE_EXPOSURE_SIM", raising=False)
    monkeypatch.setenv("COPILOT_VENUE_EXPOSURE_SIM", flag)
    import sharpedge_agent_pipeline.copilot.tools as t

    importlib.reload(t)
    try:
        names = [x.name for x in t.COPILOT_TOOLS]
        assert "get_exposure_status" in names
        assert len(names) == len(_EXPECTED_ALWAYS) + 1
    finally:
        monkeypatch.delenv("COPILOT_VENUE_EXPOSURE_SIM", raising=False)
        importlib.reload(t)
