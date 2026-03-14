"""Unit tests for GET /api/v1/value-plays endpoint.

Tests verify alpha enrichment, filtering, and badge constraints.
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)

SAMPLE_ROWS = [
    {
        "id": "play-001",
        "game": "Lakers vs Warriors",
        "bet_type": "spread",
        "side": "Lakers -3.5",
        "sportsbook": "DraftKings",
        "fair_odds": -110,
        "market_odds": -115,
        "ev_percentage": 4.5,
        "alpha_score": 0.87,
        "regime_state": "FAVORABLE",
        "created_at": "2026-03-14T00:00:00Z",
    },
    {
        "id": "play-002",
        "game": "Chiefs vs Bills",
        "bet_type": "moneyline",
        "side": "Bills ML",
        "sportsbook": "FanDuel",
        "fair_odds": 110,
        "market_odds": 105,
        "ev_percentage": 2.3,
        "alpha_score": 0.55,
        "regime_state": "NEUTRAL",
        "created_at": "2026-03-14T01:00:00Z",
    },
    {
        "id": "play-003",
        "game": "Celtics vs Heat",
        "bet_type": "total",
        "side": "Over 215.5",
        "sportsbook": "BetMGM",
        "fair_odds": -108,
        "market_odds": -115,
        "ev_percentage": 3.1,
        "alpha_score": 0.40,
        "regime_state": "UNFAVORABLE",
        "created_at": "2026-03-14T02:00:00Z",
    },
]


def test_value_plays_returns_alpha_fields() -> None:
    """GET /api/v1/value-plays must return alpha_score, alpha_badge, regime_state fields."""
    with patch(
        "sharpedge_webhooks.routes.v1.value_plays.get_active_value_plays",
        return_value=SAMPLE_ROWS,
    ):
        response = client.get("/api/v1/value-plays")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    item = data[0]
    assert "alpha_score" in item
    assert "alpha_badge" in item
    assert "regime_state" in item
    # Also verify full shape
    for key in ("id", "event", "market", "team", "our_odds", "book_odds", "expected_value", "book", "timestamp"):
        assert key in item, f"Missing key: {key}"


def test_value_plays_min_alpha_filter() -> None:
    """GET /api/v1/value-plays?min_alpha=0.7 must return only items with alpha_score >= 0.7."""
    with patch(
        "sharpedge_webhooks.routes.v1.value_plays.get_active_value_plays",
        return_value=SAMPLE_ROWS,
    ):
        response = client.get("/api/v1/value-plays?min_alpha=0.7")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert item["alpha_score"] >= 0.7


def test_value_plays_badge_values() -> None:
    """alpha_badge must be one of PREMIUM, HIGH, MEDIUM, SPECULATIVE."""
    valid_badges = {"PREMIUM", "HIGH", "MEDIUM", "SPECULATIVE"}
    with patch(
        "sharpedge_webhooks.routes.v1.value_plays.get_active_value_plays",
        return_value=SAMPLE_ROWS,
    ):
        response = client.get("/api/v1/value-plays")
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert item["alpha_badge"] in valid_badges
