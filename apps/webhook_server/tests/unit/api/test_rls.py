"""Unit tests for v1 auth dependency (RLS / JWT verification).

Tests for get_current_user FastAPI dependency — Supabase JWT verification.
Portfolio RLS tests (cross-user access) are in Plan 02 (portfolio routes).
"""

from __future__ import annotations

from typing import Annotated
from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from sharpedge_webhooks.routes.v1.deps import CurrentUser, get_current_user

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_with_auth() -> FastAPI:
    """Minimal app that requires auth on GET /protected."""
    app = FastAPI()

    @app.get("/protected")
    async def protected(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        return {"user_id": user["id"]}

    return app


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_missing_authorization_header_returns_4xx() -> None:
    """Request with no Authorization header must get HTTP 4xx (HTTPBearer raises 403)."""
    app = _make_app_with_auth()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/protected")
    # HTTPBearer with auto_error=True returns 403 when header is absent
    assert response.status_code in (401, 403)


def test_invalid_jwt_returns_401() -> None:
    """Garbage token that Supabase rejects must get HTTP 401."""
    app = _make_app_with_auth()
    client = TestClient(app, raise_server_exceptions=False)

    mock_result = MagicMock()
    mock_result.user = None

    mock_supabase_client = MagicMock()
    mock_supabase_client.auth.get_user.return_value = mock_result

    with (
        patch(
            "supabase.create_client",
            return_value=mock_supabase_client,
        ),
        patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "anon-key"},
        ),
    ):
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer garbage-token"},
        )
    assert response.status_code == 401


def test_valid_jwt_returns_user() -> None:
    """Valid token that Supabase accepts must return user dict with id and email."""
    app = _make_app_with_auth()
    client = TestClient(app, raise_server_exceptions=False)

    mock_user = MagicMock()
    mock_user.id = "user-uuid-123"
    mock_user.email = "test@example.com"

    mock_result = MagicMock()
    mock_result.user = mock_user

    mock_supabase_client = MagicMock()
    mock_supabase_client.auth.get_user.return_value = mock_result

    with (
        patch(
            "supabase.create_client",
            return_value=mock_supabase_client,
        ),
        patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_KEY": "anon-key"},
        ),
    ):
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer valid-token"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user-uuid-123"


def test_get_current_user_importable() -> None:
    """get_current_user and CurrentUser must be importable from deps."""
    assert callable(get_current_user)
    # CurrentUser is an Annotated type alias — not callable, but must exist
    assert CurrentUser is not None
