"""Tests for POST /api/v1/users/{id}/device-token (MOB-04)."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from sharpedge_webhooks.main import app
from sharpedge_webhooks.routes.v1.deps import get_current_user

client = TestClient(app)


def _mock_current_user(user_id: str = "user-123") -> None:
    """Override get_current_user dependency for testing."""
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "email": "test@test.com"}


def test_device_token_register_success(monkeypatch):
    """POST with valid JWT and payload must return 201 and registered=True."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")
    _mock_current_user("user-123")
    with patch("sharpedge_webhooks.routes.v1.notifications.create_client") as mock_sc:
        mock_table = MagicMock()
        mock_sc.return_value.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock(data=[])
        response = client.post(
            "/api/v1/users/user-123/device-token",
            json={"fcm_token": "abc123token", "platform": "ios"},
            headers={"Authorization": "Bearer testtoken"},
        )
    assert response.status_code == 201
    assert response.json()["registered"] is True


def test_device_token_requires_auth():
    """POST without Authorization header must return 401."""
    app.dependency_overrides.pop(get_current_user, None)
    response = client.post(
        "/api/v1/users/user-123/device-token",
        json={"fcm_token": "abc123token", "platform": "ios"},
        # No Authorization header
    )
    assert response.status_code == 401
