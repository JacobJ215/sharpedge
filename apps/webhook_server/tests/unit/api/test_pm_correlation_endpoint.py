"""RED test stubs for WIRE-04: GET /api/v1/prediction-markets/correlation endpoint.

These tests fail because the route is not yet registered in sharpedge_webhooks.main.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# WIRE-04: Prediction market correlation endpoint
# ---------------------------------------------------------------------------


def test_pm_correlation_returns_200() -> None:
    """GET /api/v1/prediction-markets/correlation returns 200 with list schema.

    RED: route not registered — TestClient returns 404, assertion fails.
    """
    def _check():
        response = client.get("/api/v1/prediction-markets/correlation")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Response must be a list"

    _check()


def test_pm_correlation_list_items_have_required_fields() -> None:
    """Each correlation entry has entity, sports_prob, pm_prob, correlation_score.

    RED: route not registered.
    """
    def _check():
        response = client.get("/api/v1/prediction-markets/correlation")
        assert response.status_code == 200
        data = response.json()
        if len(data) > 0:
            item = data[0]
            assert "entity" in item or "correlation_score" in item, \
                f"Correlation item missing expected fields: {item}"

    _check()


def test_pm_correlation_accepts_sport_filter() -> None:
    """GET /api/v1/prediction-markets/correlation?sport=nfl returns 200.

    RED: route not registered.
    """
    def _check():
        response = client.get("/api/v1/prediction-markets/correlation", params={"sport": "nfl"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    _check()
