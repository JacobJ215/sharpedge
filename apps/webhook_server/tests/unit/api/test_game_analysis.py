"""
RED stubs for API-02: GET /api/v1/games/{game_id}/analysis endpoint tests.
Import will fail until routes/v1/game_analysis is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.game_analysis import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1/game_analysis not yet implemented")
def test_game_analysis_returns_full_state():
    """GET /api/v1/games/{game_id}/analysis must return full analysis state."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    game_id = "game_001"  # pragma: no cover
    response = client.get(f"/api/v1/games/{game_id}/analysis")  # pragma: no cover
    assert response.status_code == 200  # pragma: no cover
    data = response.json()  # pragma: no cover
    assert "model_prediction" in data  # pragma: no cover
    assert "ev_breakdown" in data  # pragma: no cover
    assert "regime_state" in data  # pragma: no cover
    assert "key_number_proximity" in data  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1/game_analysis not yet implemented")
def test_game_analysis_404_unknown_game():
    """GET /api/v1/games/nonexistent/analysis must return 404."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    response = client.get("/api/v1/games/nonexistent/analysis")  # pragma: no cover
    assert response.status_code == 404  # pragma: no cover
