"""Monte Carlo bankroll simulation for sports betting risk analysis.

Simulates bankroll paths to estimate ruin probability and outcome percentiles.
Uses per-call RNG instances (numpy.random.default_rng) for thread safety.

IMPORTANT: Never use np.random.seed() — always use default_rng(seed) per call.
"""

from dataclasses import dataclass

import numpy as np

__all__ = ["MonteCarloResult", "simulate_bankroll"]


@dataclass(frozen=True)
class MonteCarloResult:
    """Result of a Monte Carlo bankroll simulation."""

    ruin_probability: float  # Fraction of paths that hit ruin threshold
    p05_bankroll: float  # 5th percentile final bankroll
    p50_bankroll: float  # 50th percentile (median) final bankroll
    p95_bankroll: float  # 95th percentile final bankroll
    max_drawdown_p50: float  # Median maximum drawdown across all paths
    n_paths: int  # Number of simulated paths
    n_bets: int  # Number of bets per path


def simulate_bankroll(
    win_prob: float,
    win_pct: float,  # fraction gained per win (e.g. 0.09 for +9%)
    loss_pct: float,  # fraction lost per loss (e.g. 0.10 for -10%)
    initial_bankroll: float = 1.0,
    n_paths: int = 2000,
    n_bets: int = 500,
    seed: int | None = None,  # None in production; fixed in tests only
) -> MonteCarloResult:
    """Simulate bankroll paths using Monte Carlo method.

    Args:
        win_prob: Probability of winning each bet (0.0 to 1.0)
        win_pct: Fraction of bankroll gained on a win (e.g. 0.09)
        loss_pct: Fraction of bankroll lost on a loss (e.g. 0.10)
        initial_bankroll: Starting bankroll value (default 1.0)
        n_paths: Number of simulation paths (default 2000)
        n_bets: Number of bets per path (default 500)
        seed: RNG seed for reproducibility; None for random (production)

    Returns:
        MonteCarloResult with ruin probability, percentile outcomes, and drawdown stats
    """
    rng = np.random.default_rng(seed)

    # Simulate outcomes: +win_pct or -loss_pct per bet
    outcomes = rng.choice(
        [win_pct, -loss_pct],
        size=(n_paths, n_bets),
        p=[win_prob, 1.0 - win_prob],
    )

    # Compute cumulative bankroll paths: shape (n_paths, n_bets)
    paths = initial_bankroll * np.cumprod(1.0 + outcomes, axis=1)

    # Ruin: any path that drops to <= 10% of initial bankroll at any point
    ruin_threshold = 0.1 * initial_bankroll
    ruin_mask = np.any(paths <= ruin_threshold, axis=1)
    ruin_probability = float(np.mean(ruin_mask))

    # Final bankroll percentiles
    final_bankrolls = paths[:, -1]
    p05_bankroll = float(np.percentile(final_bankrolls, 5))
    p50_bankroll = float(np.percentile(final_bankrolls, 50))
    p95_bankroll = float(np.percentile(final_bankrolls, 95))

    # Max drawdown per path: 1 - (current / running_max)
    running_max = np.maximum.accumulate(paths, axis=1)
    drawdowns = 1.0 - paths / running_max
    max_drawdowns = np.max(drawdowns, axis=1)
    max_drawdown_p50 = float(np.percentile(max_drawdowns, 50))

    return MonteCarloResult(
        ruin_probability=ruin_probability,
        p05_bankroll=p05_bankroll,
        p50_bankroll=p50_bankroll,
        p95_bankroll=p95_bankroll,
        max_drawdown_p50=max_drawdown_p50,
        n_paths=n_paths,
        n_bets=n_bets,
    )
