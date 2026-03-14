"""Unit tests for GET /api/v1/games/{game_id}/analysis endpoint.

Tests verify full analysis state shape and 404 for unknown games.
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)

SAMPLE_ROWS = [
    {
        "id": "game-001",
        "game": "Lakers vs Warriors",
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
    """GET /api/v1/games/{game_id}/analysis must return model_prediction, ev_breakdown, regime_state, key_number_proximity."""
    with patch(
        "sharpedge_webhooks.routes.v1.game_analysis.get_active_value_plays",
        return_value=SAMPLE_ROWS,
    ):
        response = client.get("/api/v1/games/game-001/analysis")
    assert response.status_code == 200
    data = response.json()
    assert "model_prediction" in data
    assert "ev_breakdown" in data
    assert "regime_state" in data
    assert "key_number_proximity" in data
    assert data["game_id"] == "game-001"
    assert "win_probability" in data["model_prediction"]
    assert "ev_percentage" in data["ev_breakdown"]


def test_game_analysis_404_unknown_game() -> None:
    """GET /api/v1/games/nonexistent/analysis must return 404."""
    with patch(
        "sharpedge_webhooks.routes.v1.game_analysis.get_active_value_plays",
        return_value=SAMPLE_ROWS,
    ):
        response = client.get("/api/v1/games/nonexistent/analysis")
    assert response.status_code == 404
