"""RED test stubs for WIRE-02: GET /api/v1/markets/dislocation endpoint.

These tests fail because the route is not yet registered in sharpedge_webhooks.main.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# WIRE-02: Dislocation endpoint
# ---------------------------------------------------------------------------


def test_get_dislocation_returns_200() -> None:
    """GET /api/v1/markets/dislocation?market_id=nfl_game_1 returns 200 with expected schema.

    RED: route not registered — TestClient returns 404, assertion fails.
    """

    def _check():
        response = client.get("/api/v1/markets/dislocation", params={"market_id": "nfl_game_1"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "consensus_prob" in data, "Response missing 'consensus_prob'"
        assert "scores" in data, "Response missing 'scores'"
        assert isinstance(data["scores"], dict), "'scores' must be a dict"

    _check()


def test_get_dislocation_requires_market_id() -> None:
    """GET /api/v1/markets/dislocation without market_id returns 422.

    RED: route not registered — TestClient returns 404, not 422.
    """

    def _check():
        response = client.get("/api/v1/markets/dislocation")
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

    _check()


def test_get_dislocation_returns_dislocation_bps_field() -> None:
    """Response schema includes dislocation_bps numeric field.

    RED: route not registered.
    """

    def _check():
        response = client.get("/api/v1/markets/dislocation", params={"market_id": "test_market"})
        assert response.status_code == 200
        data = response.json()
        assert "dislocation_bps" in data, "Response missing 'dislocation_bps'"
        assert isinstance(data["dislocation_bps"], (int, float))

    _check()
