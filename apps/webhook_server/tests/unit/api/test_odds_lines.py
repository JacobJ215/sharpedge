"""Odds v1 routes — configuration and error paths."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)


def test_odds_games_503_without_api_key() -> None:
    with patch(
        "sharpedge_webhooks.routes.v1.odds_lines._config_odds_key",
        return_value="",
    ):
        r = client.get("/api/v1/odds/games?sport=NFL")
    assert r.status_code == 503
    assert "not configured" in r.json()["detail"].lower()


def test_odds_bad_sport_returns_400() -> None:
    """Invalid sport fails before Odds API client is constructed."""
    r = client.get("/api/v1/odds/games?sport=XYZ")
    assert r.status_code == 400
    body = r.json()
    assert "detail" in body
    assert "unsupported" in str(body["detail"]).lower()
