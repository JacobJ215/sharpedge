"""compose_alpha node: computes composite BettingAlpha from ev + mc signals.

Calls compose_alpha() from sharpedge_models.alpha. No LLM, no network.
Under 60 lines.
"""
from __future__ import annotations

import logging

from sharpedge_analytics.regime import REGIME_SCALE, RegimeState
from sharpedge_models.alpha import compose_alpha as _compose_alpha, BettingAlpha

logger = logging.getLogger("sharpedge.agent.compose_alpha")


def compose_alpha(state: dict) -> dict:
    """Compose the betting alpha score from EV and Monte Carlo signals.

    Derives edge_score, regime_scale, survival_prob, and confidence_mult from
    ev_result, regime_result, and mc_result. Calls compose_alpha() pure function.

    Args:
        state: BettingAnalysisState with ev_result, regime_result, mc_result.

    Returns:
        Partial state dict with alpha (BettingAlpha).
    """
    ev_result: dict = state.get("ev_result") or {}
    regime_result = state.get("regime_result")
    mc_result = state.get("mc_result")

    # edge_score: P(edge > 0) from EV calculation
    edge_score: float = ev_result.get("prob_edge_positive", 0.5)

    # regime_scale: multiplier from regime classification
    if regime_result is not None:
        regime_state = regime_result.regime
        regime_scale: float = REGIME_SCALE.get(regime_state, 1.0)
    else:
        regime_scale = 1.0

    # survival_prob: 1 - ruin_probability from Monte Carlo
    if mc_result is not None:
        survival_prob: float = 1.0 - getattr(mc_result, "ruin_probability", 0.0)
    else:
        survival_prob = 0.95  # conservative default

    # confidence_mult: placeholder 1.0 until Phase 5 calibration
    confidence_mult: float = 1.0

    try:
        alpha: BettingAlpha = _compose_alpha(
            edge_score=edge_score,
            regime_scale=regime_scale,
            survival_prob=survival_prob,
            confidence_mult=confidence_mult,
        )
    except Exception as exc:
        logger.warning("compose_alpha failed: %s", exc)
        return {"alpha": None, "quality_warnings": [f"compose_alpha failed: {exc}"]}

    return {"alpha": alpha}
