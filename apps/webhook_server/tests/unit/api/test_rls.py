"""
RED stubs for API-06: Row-Level Security enforcement tests.
Import will fail until routes/v1 is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.value_plays import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1 not yet implemented")
def test_rls_blocks_cross_user_portfolio():
    """GET /api/v1/users/{other_user_id}/portfolio with different user's JWT
    must return 403 (RLS blocks cross-user access)."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    other_user_id = "00000000-0000-0000-0000-000000000002"  # pragma: no cover
    headers = {"Authorization": "Bearer <jwt_for_user_1>"}  # pragma: no cover
    response = client.get(f"/api/v1/users/{other_user_id}/portfolio", headers=headers)  # pragma: no cover
    assert response.status_code == 403  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1 not yet implemented")
def test_rls_allows_own_portfolio():
    """GET /api/v1/users/{own_id}/portfolio with correct JWT must return 200."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    own_user_id = "00000000-0000-0000-0000-000000000001"  # pragma: no cover
    headers = {"Authorization": "Bearer <jwt_for_user_1>"}  # pragma: no cover
    response = client.get(f"/api/v1/users/{own_user_id}/portfolio", headers=headers)  # pragma: no cover
    assert response.status_code == 200  # pragma: no cover
