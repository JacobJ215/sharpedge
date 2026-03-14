"""Failing test stubs for QUANT-02: Monte Carlo bankroll simulation."""
import pytest


def test_simulate_bankroll_returns_result():
    """simulate_bankroll returns MonteCarloResult with expected fields."""
    from sharpedge_models.monte_carlo import simulate_bankroll, MonteCarloResult
    result = simulate_bankroll(win_prob=0.55, win_pct=0.09, loss_pct=0.10, seed=42)
    assert isinstance(result, MonteCarloResult)
    assert 0.0 <= result.ruin_probability <= 1.0
    assert result.p05_bankroll <= result.p50_bankroll <= result.p95_bankroll


def test_thread_safety():
    """Two calls with seed=None produce different distributions."""
    from sharpedge_models.monte_carlo import simulate_bankroll
    r1 = simulate_bankroll(win_prob=0.55, win_pct=0.09, loss_pct=0.10, seed=None)
    r2 = simulate_bankroll(win_prob=0.55, win_pct=0.09, loss_pct=0.10, seed=None)
    # Different seeds -> different paths -> different ruin probabilities (extremely rare collision)
    assert r1.p50_bankroll != r2.p50_bankroll or r1.ruin_probability != r2.ruin_probability


def test_seeded_reproducibility():
    """Same seed produces identical results."""
    from sharpedge_models.monte_carlo import simulate_bankroll
    r1 = simulate_bankroll(win_prob=0.55, win_pct=0.09, loss_pct=0.10, seed=42)
    r2 = simulate_bankroll(win_prob=0.55, win_pct=0.09, loss_pct=0.10, seed=42)
    assert r1.ruin_probability == r2.ruin_probability
    assert r1.p50_bankroll == r2.p50_bankroll
