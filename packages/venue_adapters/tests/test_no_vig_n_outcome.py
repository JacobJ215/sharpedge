"""RED stubs: N-outcome Shin devig extension to no_vig.py. PRICE-01."""
import pytest
from sharpedge_models.no_vig import devig_shin_n_outcome  # ImportError until Wave 3


def test_two_outcome_matches_binary_shin():
    """devig_shin_n_outcome on 2 outcomes must match existing devig_shin()."""
    implied = [0.52, 0.54]  # sum > 1, has vig
    fair = devig_shin_n_outcome(implied)
    assert len(fair) == 2
    assert abs(sum(fair) - 1.0) < 1e-6


def test_three_outcome_sums_to_one():
    """Soccer three-way: home/draw/away."""
    implied = [0.45, 0.30, 0.35]  # sum = 1.10
    fair = devig_shin_n_outcome(implied)
    assert len(fair) == 3
    assert abs(sum(fair) - 1.0) < 1e-6


def test_three_outcome_fair_probs_in_range():
    implied = [0.45, 0.30, 0.35]
    fair = devig_shin_n_outcome(implied)
    for p in fair:
        assert 0.0 < p < 1.0


def test_no_vig_market_returns_unchanged():
    """If implied probs already sum to 1.0, return as-is (within tolerance)."""
    implied = [0.40, 0.35, 0.25]  # sum = 1.0
    fair = devig_shin_n_outcome(implied)
    assert abs(sum(fair) - 1.0) < 1e-6


def test_n_outcome_futures_market():
    """Championship futures: 8 teams, sum > 1."""
    implied = [0.15, 0.14, 0.13, 0.12, 0.11, 0.10, 0.09, 0.20]  # sum = 1.04
    fair = devig_shin_n_outcome(implied)
    assert len(fair) == 8
    assert abs(sum(fair) - 1.0) < 1e-6


def test_sharp_reduction_direction():
    """Fair probs must be <= implied probs (removing bookmaker margin)."""
    implied = [0.52, 0.54]
    fair = devig_shin_n_outcome(implied)
    assert fair[0] < implied[0] or fair[1] < implied[1]
