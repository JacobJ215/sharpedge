"""
RED stubs for POST /api/v1/users/{id}/device-token endpoint tests (MOB-04).
Import will fail until routes/v1/notifications is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.notifications import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1/notifications not yet implemented")
def test_device_token_register_success():
    """POST /api/v1/users/{user_id}/device-token with valid JWT and payload must return 201."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    user_id = "00000000-0000-0000-0000-000000000001"  # pragma: no cover
    response = client.post(  # pragma: no cover
        f"/api/v1/users/{user_id}/device-token",
        json={"fcm_token": "abc123", "platform": "ios"},
        headers={"Authorization": "Bearer <valid_jwt>"},
    )
    assert response.status_code == 201  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1/notifications not yet implemented")
def test_device_token_requires_auth():
    """POST /api/v1/users/{user_id}/device-token without Authorization header must return 401."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    user_id = "00000000-0000-0000-0000-000000000001"  # pragma: no cover
    response = client.post(  # pragma: no cover
        f"/api/v1/users/{user_id}/device-token",
        json={"fcm_token": "abc123", "platform": "ios"},
    )
    assert response.status_code == 401  # pragma: no cover
