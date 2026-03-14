"""
RED stubs for API-05: POST /api/v1/bankroll/simulate endpoint tests.
Import will fail until routes/v1/bankroll is implemented — that is intentional.
"""
import pytest

# This import does not exist yet — ImportError is the RED state.
# Tests are skipped so collection succeeds without failures.
# from sharpedge_webhooks.routes.v1.bankroll import router  # noqa: F401


@pytest.mark.skip(reason="RED — routes/v1/bankroll not yet implemented")
def test_bankroll_simulate_returns_monte_carlo():
    """POST /api/v1/bankroll/simulate must return Monte Carlo analytics shape."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    payload = {  # pragma: no cover
        "bankroll": 1000,
        "bet_size": 50,
        "num_bets": 100,
        "win_rate": 0.55,
    }
    response = client.post("/api/v1/bankroll/simulate", json=payload)  # pragma: no cover
    assert response.status_code == 200  # pragma: no cover
    data = response.json()  # pragma: no cover
    assert "ruin_probability" in data  # pragma: no cover
    assert "p5_outcome" in data  # pragma: no cover
    assert "p50_outcome" in data  # pragma: no cover
    assert "p95_outcome" in data  # pragma: no cover
    assert "max_drawdown" in data  # pragma: no cover


@pytest.mark.skip(reason="RED — routes/v1/bankroll not yet implemented")
def test_bankroll_simulate_no_auth_required():
    """POST /api/v1/bankroll/simulate without auth header must still return 200 (public endpoint)."""
    from httpx import Client  # pragma: no cover
    client = Client(base_url="http://testserver")  # pragma: no cover
    payload = {  # pragma: no cover
        "bankroll": 1000,
        "bet_size": 50,
        "num_bets": 100,
        "win_rate": 0.55,
    }
    response = client.post("/api/v1/bankroll/simulate", json=payload)  # pragma: no cover
    assert response.status_code == 200  # pragma: no cover
