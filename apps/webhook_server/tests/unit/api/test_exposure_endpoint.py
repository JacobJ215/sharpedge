"""RED test stubs for WIRE-02: GET /api/v1/bankroll/exposure endpoint.

These tests fail because the route is not yet registered in sharpedge_webhooks.main.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# WIRE-02: Exposure endpoint
# ---------------------------------------------------------------------------


def test_get_exposure_returns_200() -> None:
    """GET /api/v1/bankroll/exposure returns 200 with expected schema.

    RED: route not registered — TestClient returns 404, assertion fails.
    """

    def _check():
        response = client.get("/api/v1/bankroll/exposure")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "total_exposure" in data, "Response missing 'total_exposure'"
        assert "bankroll" in data, "Response missing 'bankroll'"
        assert "venues" in data, "Response missing 'venues'"
        assert isinstance(data["venues"], list), "'venues' must be a list"

    _check()


def test_get_exposure_venues_have_required_fields() -> None:
    """Each venue entry in the response has venue, exposure, pct fields.

    RED: route not registered.
    """

    def _check():
        response = client.get("/api/v1/bankroll/exposure")
        assert response.status_code == 200
        data = response.json()
        for venue in data["venues"]:
            assert "venue" in venue, f"Venue entry missing 'venue': {venue}"
            assert "exposure" in venue, f"Venue entry missing 'exposure': {venue}"
            assert "pct" in venue, f"Venue entry missing 'pct': {venue}"

    _check()
