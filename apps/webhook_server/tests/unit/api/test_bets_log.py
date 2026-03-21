"""Tests for POST /api/v1/bets."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

USER_ID = "00000000-0000-0000-0000-000000000099"
INTERNAL_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

PLAY_ROW = {
    "id": "play-1",
    "game": "Lakers vs Celtics",
    "sport": "NBA",
    "bet_type": "spread",
    "side": "Lakers -3",
    "market_odds": -110,
    "sportsbook": "DraftKings",
}


@pytest.fixture
def mock_bet():
    b = MagicMock()
    b.id = "bet-new-1"
    b.game = "Lakers vs Celtics"
    b.selection = "Lakers -3"
    b.stake = Decimal("100.00")
    b.odds = -110
    b.units = Decimal("2.00")
    return b


@pytest.fixture
def app_bets(mock_bet):
    from sharpedge_webhooks.routes.v1 import deps
    from sharpedge_webhooks.routes.v1.bets import router

    app = FastAPI()

    async def mock_user():
        return {"id": USER_ID, "email": "t@example.com"}

    app.dependency_overrides[deps.get_current_user] = mock_user
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client_bets(app_bets, mock_bet):
    with (
        patch(
            "sharpedge_webhooks.routes.v1.bets.get_internal_user_id_by_supabase_auth",
            return_value=INTERNAL_ID,
        ),
        patch(
            "sharpedge_webhooks.routes.v1.bets.get_value_play",
            return_value=PLAY_ROW,
        ),
        patch(
            "sharpedge_webhooks.routes.v1.bets.get_unit_size_for_user",
            return_value=Decimal("50"),
        ),
        patch(
            "sharpedge_webhooks.routes.v1.bets.create_bet",
            return_value=mock_bet,
        ),TestClient(app_bets, raise_server_exceptions=True) as c
    ):
        yield c


def test_log_bet_requires_auth():
    from sharpedge_webhooks.routes.v1.bets import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app, raise_server_exceptions=True)
    r = client.post("/api/v1/bets", json={})
    assert r.status_code == 401


def test_log_bet_201(client_bets):
    r = client_bets.post(
        "/api/v1/bets",
        headers={"Authorization": "Bearer fake"},
        json={
            "play_id": "play-1",
            "event": "Lakers vs Celtics",
            "market": "spread",
            "team": "Lakers -3",
            "book": "DraftKings",
            "stake": 100,
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"] == "bet-new-1"
    assert data["odds"] == -110


def test_log_bet_event_mismatch(client_bets):
    r = client_bets.post(
        "/api/v1/bets",
        headers={"Authorization": "Bearer fake"},
        json={
            "play_id": "play-1",
            "event": "Wrong Game",
            "market": "spread",
            "team": "Lakers -3",
            "book": "DraftKings",
            "stake": 100,
        },
    )
    assert r.status_code == 400
