"""
Tests for API-05: POST /api/v1/bankroll/simulate endpoint.
Public endpoint — no auth required. Mocks simulate_bankroll from Phase 1.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

SIMULATE_PAYLOAD = {
    "bankroll": 1000,
    "bet_size": 50,
    "num_bets": 100,
    "win_rate": 0.55,
}

MOCK_RESULT = {
    "ruin_probability": 0.03,
    "p5_outcome": 750.0,
    "p50_outcome": 1100.0,
    "p95_outcome": 1500.0,
    "max_drawdown": 250.0,
}


@pytest.fixture
def app():
    from fastapi import FastAPI

    from sharpedge_webhooks.routes.v1.bankroll import router

    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1")
    return _app


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=True)


def test_bankroll_simulate_no_auth_required(client):
    """POST /api/v1/bankroll/simulate without auth header must return 200 (public endpoint)."""
    with patch("sharpedge_webhooks.routes.v1.bankroll.simulate_bankroll", return_value=MOCK_RESULT):
        response = client.post("/api/v1/bankroll/simulate", json=SIMULATE_PAYLOAD)
    assert response.status_code == 200


def test_bankroll_simulate_returns_monte_carlo_shape(client):
    """POST /api/v1/bankroll/simulate must return Monte Carlo analytics shape."""
    with patch("sharpedge_webhooks.routes.v1.bankroll.simulate_bankroll", return_value=MOCK_RESULT):
        response = client.post("/api/v1/bankroll/simulate", json=SIMULATE_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "ruin_probability" in data
    assert "p5_outcome" in data
    assert "p50_outcome" in data
    assert "p95_outcome" in data
    assert "max_drawdown" in data
