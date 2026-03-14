"""
Tests for API-04: GET /api/v1/users/{id}/portfolio endpoint.
Uses TestClient with mocked auth dependency and DB query functions.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


USER_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def mock_summary():
    summary = MagicMock()
    summary.roi = 0.12
    summary.win_rate = 55.0
    summary.total_bets = 100
    summary.wins = 55
    summary.losses = 45
    return summary


@pytest.fixture
def mock_bets():
    return [
        {
            "id": "bet-1",
            "game": "Lakers vs Celtics",
            "stake": "50.00",
            "sportsbook": "DraftKings",
            "result": "win",
            "profit": "45.00",
            "clv": "0.04",
        },
        {
            "id": "bet-2",
            "game": "Chiefs vs Ravens",
            "stake": "100.00",
            "sportsbook": "FanDuel",
            "result": "pending",
            "profit": None,
            "clv": None,
        },
    ]


@pytest.fixture
def app_with_mocked_auth(mock_summary, mock_bets):
    """FastAPI app with portfolio router and mocked get_current_user."""
    from fastapi import FastAPI
    from sharpedge_webhooks.routes.v1 import deps
    from sharpedge_webhooks.routes.v1.portfolio import router

    _app = FastAPI()

    # Override auth dependency to return a known user
    async def mock_get_current_user():
        return {"id": USER_ID, "email": "test@example.com"}

    _app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    _app.include_router(router, prefix="/api/v1")
    return _app


@pytest.fixture
def authed_client(app_with_mocked_auth, mock_summary, mock_bets):
    with (
        patch("sharpedge_webhooks.routes.v1.portfolio.get_performance_summary", return_value=mock_summary),
        patch("sharpedge_webhooks.routes.v1.portfolio.get_user_bets_history", return_value=mock_bets),
    ):
        with TestClient(app_with_mocked_auth, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture
def unauthed_app():
    """FastAPI app with portfolio router but NO auth override (will 401)."""
    from fastapi import FastAPI
    from sharpedge_webhooks.routes.v1.portfolio import router

    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1")
    return _app


def test_portfolio_requires_auth():
    """GET /api/v1/users/{id}/portfolio without Authorization header must return 401."""
    from fastapi import FastAPI
    from sharpedge_webhooks.routes.v1.portfolio import router

    _app = FastAPI()
    _app.include_router(router, prefix="/api/v1")
    client = TestClient(_app, raise_server_exceptions=True)
    response = client.get(f"/api/v1/users/{USER_ID}/portfolio")
    assert response.status_code == 401


def test_portfolio_shape_with_mocked_auth(authed_client):
    """GET /api/v1/users/{id}/portfolio returns required analytics fields."""
    response = authed_client.get(
        f"/api/v1/users/{USER_ID}/portfolio",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "roi" in data
    assert "win_rate" in data
    assert "clv_average" in data
    assert "drawdown" in data
    assert "active_bets" in data
    assert isinstance(data["active_bets"], list)
