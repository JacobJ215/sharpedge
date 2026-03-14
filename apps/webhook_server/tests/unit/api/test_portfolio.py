"""
RED stubs for API-04: GET /api/v1/users/{id}/portfolio endpoint tests.
Import will fail until routes/v1/portfolio is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.portfolio import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1/portfolio not yet implemented")
def test_portfolio_shape():
    """GET /api/v1/users/{id}/portfolio must return full portfolio analytics shape."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    user_id = "00000000-0000-0000-0000-000000000001"  # pragma: no cover
    response = client.get(  # pragma: no cover
        f"/api/v1/users/{user_id}/portfolio",
        headers={"Authorization": "Bearer <valid_jwt>"},
    )
    assert response.status_code == 200  # pragma: no cover
    data = response.json()  # pragma: no cover
    assert "roi" in data  # pragma: no cover
    assert "win_rate" in data  # pragma: no cover
    assert "clv_average" in data  # pragma: no cover
    assert "drawdown" in data  # pragma: no cover
    assert "active_bets" in data  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1/portfolio not yet implemented")
def test_portfolio_requires_auth():
    """GET /api/v1/users/{id}/portfolio without Authorization header must return 401."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    user_id = "00000000-0000-0000-0000-000000000001"  # pragma: no cover
    response = client.get(f"/api/v1/users/{user_id}/portfolio")  # pragma: no cover
    assert response.status_code == 401  # pragma: no cover
