"""Unit tests for copilot game_resolve_logic (OddsClient mocked)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from sharpedge_odds.models import Game


def _game(
    gid: str,
    home: str,
    away: str,
    hours: int = 0,
) -> Game:
    t = datetime(2026, 3, 22, 0, 0, 0, tzinfo=timezone.utc)
    return Game(
        id=gid,
        sport_key="basketball_nba",
        sport_title="NBA",
        commence_time=t,
        home_team=home,
        away_team=away,
        bookmakers=[],
    )


@patch.dict("os.environ", {"ODDS_API_KEY": "test-key"}, clear=False)
@patch("sharpedge_agent_pipeline.copilot.game_resolve_logic.OddsClient")
def test_search_games_impl_returns_capped_list(mock_client_cls):
    g1 = _game("a1", "Los Angeles Lakers", "Boston Celtics")
    g2 = _game("a2", "Phoenix Suns", "Denver Nuggets")
    instance = MagicMock()
    instance.get_odds.return_value = [g2, g1]
    instance.close = MagicMock()
    mock_client_cls.return_value = instance

    from sharpedge_agent_pipeline.copilot.game_resolve_logic import search_games_impl

    out = search_games_impl("NBA", "Lakers")
    assert out["count"] == 1
    assert len(out["games"]) == 1
    assert out["games"][0]["game_id"] == "a1"
    assert out["games"][0]["home_team"] == "Los Angeles Lakers"
    instance.close.assert_called_once()


@patch.dict("os.environ", {"ODDS_API_KEY": "test-key"}, clear=False)
@patch("sharpedge_agent_pipeline.copilot.game_resolve_logic.OddsClient")
def test_search_games_impl_no_api_key(mock_client_cls):
    from sharpedge_agent_pipeline.copilot.game_resolve_logic import search_games_impl

    with patch.dict("os.environ", {"ODDS_API_KEY": ""}, clear=False):
        out = search_games_impl("NBA", "")
    assert out["count"] == 0
    assert out["games"] == []
    assert "error" in out
    mock_client_cls.assert_not_called()


@patch.dict("os.environ", {"ODDS_API_KEY": "test-key"}, clear=False)
@patch("sharpedge_agent_pipeline.copilot.game_resolve_logic.OddsClient")
def test_resolve_game_impl_find_game_hit(mock_client_cls):
    g = _game("x9", "Lakers", "Celtics")
    instance = MagicMock()
    instance.find_game.return_value = g
    instance.close = MagicMock()
    mock_client_cls.return_value = instance

    from sharpedge_agent_pipeline.copilot.game_resolve_logic import resolve_game_impl

    out = resolve_game_impl("NBA", "Lakers")
    assert out.get("ambiguous") is False
    assert out["game"]["game_id"] == "x9"
    assert out["candidates"] == []
    instance.find_game.assert_called_once()
    instance.close.assert_called_once()


@patch.dict("os.environ", {"ODDS_API_KEY": "test-key"}, clear=False)
@patch("sharpedge_agent_pipeline.copilot.game_resolve_logic.OddsClient")
def test_resolve_game_impl_ambiguous_candidates(mock_client_cls):
    """find_game misses; two strong fuzzy matches → candidates."""
    g1 = _game("b1", "Los Angeles Lakers", "Boston Celtics")
    g2 = _game("b2", "Los Angeles Clippers", "Boston Celtics")
    instance = MagicMock()
    instance.find_game.return_value = None
    instance.get_odds.return_value = [g1, g2]
    instance.close = MagicMock()
    mock_client_cls.return_value = instance

    from sharpedge_agent_pipeline.copilot.game_resolve_logic import resolve_game_impl

    out = resolve_game_impl("NBA", "Lakers Celtics")
    assert out.get("ambiguous") is True
    assert out["game"] is None
    assert len(out["candidates"]) >= 2
