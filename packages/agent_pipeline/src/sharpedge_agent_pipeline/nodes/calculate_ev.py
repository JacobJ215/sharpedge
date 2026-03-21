"""calculate_ev node: runs Monte Carlo bankroll simulation.

Calls simulate_bankroll from sharpedge_models.monte_carlo. No LLM, no network.
Appends quality_warnings if ruin_probability > 0.05.
Under 60 lines.
"""

from __future__ import annotations

import logging

from sharpedge_models.monte_carlo import MonteCarloResult, simulate_bankroll

logger = logging.getLogger("sharpedge.agent.calculate_ev")

_HIGH_RUIN_THRESHOLD = 0.05


def calculate_ev(state: dict) -> dict:
    """Run Monte Carlo simulation using ev_result data.

    Derives win_prob, win_pct, and loss_pct from the ev_result dict set by
    run_models. Runs 2000-path simulation.

    Args:
        state: BettingAnalysisState with ev_result set by run_models.

    Returns:
        Partial state dict with mc_result and optionally quality_warnings.
    """
    ev_result: dict = state.get("ev_result") or {}

    # Derive simulation inputs from EV calculation
    model_prob_pct: float = ev_result.get("model_prob", 52.0)
    win_prob: float = model_prob_pct / 100.0

    # Kelly half as a fraction of bankroll for sizing
    kelly_half_pct: float = ev_result.get("kelly_half", 2.5)
    stake_frac: float = max(0.005, min(kelly_half_pct / 100.0, 0.25))

    # Approximate win/loss pcts from stake and implied odds
    win_pct: float = stake_frac * 0.9  # approximate net gain per win
    loss_pct: float = stake_frac  # lose the full stake

    try:
        mc: MonteCarloResult = simulate_bankroll(
            win_prob=win_prob,
            win_pct=win_pct,
            loss_pct=loss_pct,
            n_paths=2000,
            n_bets=500,
        )
    except Exception as exc:
        logger.warning("simulate_bankroll failed: %s", exc)
        return {
            "mc_result": None,
            "quality_warnings": [f"calculate_ev Monte Carlo failed: {exc}"],
        }

    output: dict = {"mc_result": mc}

    if mc.ruin_probability > _HIGH_RUIN_THRESHOLD:
        output["quality_warnings"] = [
            f"High ruin probability ({mc.ruin_probability:.1%}) — consider reducing stake size"
        ]

    return output
