"""Unit tests for GET /api/v1/games/{game_id}/analysis endpoint.

Tests verify full analysis state shape and 404 for unknown games.
"""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from sharpedge_db.queries.injuries import teams_from_game_label
from sharpedge_webhooks.main import app

client = TestClient(app)

SAMPLE_ROWS = [
    {
        "id": "game-001",
        "game": "Lakers vs Warriors",
        "sport": "NBA",
        "bet_type": "spread",
        "side": "Lakers -3.5",
        "sportsbook": "DraftKings",
        "fair_odds": -110,
        "market_odds": -115,
        "ev_percentage": 4.5,
        "win_prob": 0.58,
        "confidence": "HIGH",
        "alpha_score": 0.87,
        "alpha_badge": "PREMIUM",
        "regime_state": "FAVORABLE",
        "key_number_proximity": 3.0,
    },
]


def test_game_analysis_returns_full_state() -> None:
    """GET /api/v1/games/{game_id}/analysis returns core fields + injuries list."""
    with (
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.get_active_value_plays",
            return_value=SAMPLE_ROWS,
        ),
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.load_injuries_for_analysis",
            return_value=[],
        ),
    ):
        response = client.get("/api/v1/games/game-001/analysis")
    assert response.status_code == 200
    data = response.json()
    assert "model_prediction" in data
    assert "ev_breakdown" in data
    assert "regime_state" in data
    assert "key_number_proximity" in data
    assert "injuries" in data
    assert data["injuries"] == []
    assert data["game_id"] == "game-001"
    assert "win_probability" in data["model_prediction"]
    assert "ev_percentage" in data["ev_breakdown"]


def test_game_analysis_injuries_strip_populated() -> None:
    """Injuries strip forwards rows from load_injuries_for_analysis."""
    inj = [
        {
            "team": "Los Angeles Lakers",
            "player_name": "A. Player",
            "position": "PG",
            "status": "Out",
            "injury_type": "Ankle",
            "is_key_player": True,
            "impact_rating": 7.0,
        },
    ]
    with (
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.get_active_value_plays",
            return_value=SAMPLE_ROWS,
        ),
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.load_injuries_for_analysis",
            return_value=inj,
        ),
    ):
        response = client.get("/api/v1/games/game-001/analysis")
    assert response.status_code == 200
    data = response.json()
    assert len(data["injuries"]) == 1
    assert data["injuries"][0]["player_name"] == "A. Player"
    assert data["injuries"][0]["is_key_player"] is True


def test_teams_from_game_label_splits_vs() -> None:
    """Helper splits common game title separators."""
    assert teams_from_game_label("Lakers vs Warriors") == ["Lakers", "Warriors"]
    assert teams_from_game_label("Chiefs @ Raiders") == ["Chiefs", "Raiders"]


def test_game_analysis_404_unknown_game() -> None:
    """GET /api/v1/games/nonexistent/analysis must return 404."""
    with (
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.get_active_value_plays",
            return_value=SAMPLE_ROWS,
        ),
        patch(
            "sharpedge_webhooks.routes.v1.game_analysis.load_injuries_for_analysis",
            return_value=[],
        ),
    ):
        response = client.get("/api/v1/games/nonexistent/analysis")
    assert response.status_code == 404
