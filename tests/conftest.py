import pytest


@pytest.fixture
def sample_ev_calc():
    """Minimal EVCalculation-like dict for testing alpha composition."""
    return {"prob_edge_positive": 0.72, "odds": -110}


@pytest.fixture
def sample_game_inputs():
    """Inputs for regime and key number tests."""
    return {
        "ticket_pct": 0.70,
        "handle_pct": 0.45,
        "line_move_pts": 1.0,
        "move_velocity": 0.2,
        "book_alignment": 0.6,
    }
