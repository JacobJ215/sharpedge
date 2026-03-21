"""Alpha score composition for sports betting signal quality assessment.

Combines edge probability, regime scale, survival probability, and confidence
into a single composite alpha score with a quality badge.

Pitfall guard: EDGE_SCORE_FLOOR prevents zero-alpha on tiny edges by capping
badge at SPECULATIVE when edge_score is below the floor — multipliers are NOT
applied in this case.
"""

from dataclasses import dataclass
from typing import Literal

__all__ = ["EDGE_SCORE_FLOOR", "BettingAlpha", "compose_alpha"]

# Below this threshold, badge is SPECULATIVE regardless of multipliers.
# Guards against amplifying noise-level edges into falsely high alpha scores.
EDGE_SCORE_FLOOR = 0.05


@dataclass(frozen=True)
class BettingAlpha:
    """Composite alpha score with quality classification."""

    alpha: float                # Composite alpha value
    edge_score: float           # Input prob_edge_positive from EVCalculation
    regime_scale: float         # Input scale from RegimeClassification
    survival_prob: float        # Input 1 - ruin_probability from MonteCarloResult
    confidence_mult: float      # Calibration multiplier (1.0 in Phase 1)
    quality_badge: Literal["PREMIUM", "HIGH", "MEDIUM", "SPECULATIVE"]


def compose_alpha(
    edge_score: float,          # prob_edge_positive from EVCalculation
    regime_scale: float,        # RegimeClassification.scale (0.8–1.4)
    survival_prob: float,       # 1.0 - MonteCarloResult.ruin_probability
    confidence_mult: float,     # calibration multiplier (1.0 in Phase 1; Phase 5 updates)
) -> BettingAlpha:
    """Compose a betting alpha score from component signals.

    Formula (post-floor): edge_score * regime_scale * survival_prob * confidence_mult

    The EDGE_SCORE_FLOOR guard short-circuits to SPECULATIVE before applying
    multipliers when edge_score < 0.05, preventing noise amplification.

    Args:
        edge_score: Probability that the edge is positive (0.0 to 1.0)
        regime_scale: Regime-based multiplier from RegimeClassification
        survival_prob: 1.0 minus ruin probability from Monte Carlo simulation
        confidence_mult: Calibration multiplier (1.0 until Phase 5 calibration)

    Returns:
        BettingAlpha with composite alpha score and quality badge
    """
    # Floor guard: sub-threshold edge scores are SPECULATIVE without amplification
    if edge_score < EDGE_SCORE_FLOOR:
        return BettingAlpha(
            alpha=edge_score,
            edge_score=edge_score,
            regime_scale=regime_scale,
            survival_prob=survival_prob,
            confidence_mult=confidence_mult,
            quality_badge="SPECULATIVE",
        )

    alpha = edge_score * regime_scale * survival_prob * confidence_mult

    # Badge thresholds applied to post-multiplier alpha
    if alpha >= 0.15:
        badge: Literal["PREMIUM", "HIGH", "MEDIUM", "SPECULATIVE"] = "PREMIUM"
    elif alpha >= 0.08:
        badge = "HIGH"
    elif alpha >= 0.03:
        badge = "MEDIUM"
    else:
        badge = "SPECULATIVE"

    return BettingAlpha(
        alpha=alpha,
        edge_score=edge_score,
        regime_scale=regime_scale,
        survival_prob=survival_prob,
        confidence_mult=confidence_mult,
        quality_badge=badge,
    )
