"""Prediction market regime classifier.

5-state rule-based classifier using 4 market signals.
Mirrors sports regime.py pattern: deterministic, priority-ordered rules, no ML.

Rule priority order (first match wins):
1. PRE_RESOLUTION: hours_to_close < 24
2. DISCOVERY: hours_since_created < 48
3. NEWS_CATALYST: volume_spike_ratio > 3.0
4. CONSENSUS: price_variance < 0.02 (tight spread proxy)
5. SHARP_DISAGREEMENT: default fallback
"""

from dataclasses import dataclass
from enum import Enum

__all__ = [
    "PMRegimeState",
    "PMRegimeClassification",
    "PM_REGIME_THRESHOLDS",
    "PM_REGIME_SCALE",
    "classify_pm_regime",
]


class PMRegimeState(str, Enum):
    DISCOVERY = "DISCOVERY"
    CONSENSUS = "CONSENSUS"
    NEWS_CATALYST = "NEWS_CATALYST"
    PRE_RESOLUTION = "PRE_RESOLUTION"
    SHARP_DISAGREEMENT = "SHARP_DISAGREEMENT"


PM_REGIME_THRESHOLDS: dict[PMRegimeState, float] = {
    PMRegimeState.DISCOVERY: 2.0,
    PMRegimeState.CONSENSUS: 3.0,
    PMRegimeState.NEWS_CATALYST: 3.0,
    PMRegimeState.PRE_RESOLUTION: 5.0,
    PMRegimeState.SHARP_DISAGREEMENT: 3.0,
}

PM_REGIME_SCALE: dict[PMRegimeState, float] = {
    PMRegimeState.DISCOVERY: 1.2,
    PMRegimeState.CONSENSUS: 1.0,
    PMRegimeState.NEWS_CATALYST: 0.9,
    PMRegimeState.PRE_RESOLUTION: 0.8,
    PMRegimeState.SHARP_DISAGREEMENT: 1.1,
}


@dataclass(frozen=True)
class PMRegimeClassification:
    """Result of PM regime classification."""

    regime: PMRegimeState
    confidence: float
    edge_threshold_pct: float  # regime-adjusted threshold in percentage points
    scale: float               # for alpha composition


def classify_pm_regime(
    hours_to_close: float,
    hours_since_created: float,
    volume_spike_ratio: float,  # 24h vol / 7d avg; use 1.0 when unavailable
    price_variance: float,      # bid-ask spread proxy; use spread when history unavailable
) -> PMRegimeClassification:
    """Classify a prediction market's regime using 4 signals.

    Rules are evaluated in priority order; first match wins.

    Args:
        hours_to_close: Hours remaining until market closes.
        hours_since_created: Hours elapsed since market was created.
        volume_spike_ratio: Ratio of 24h volume to 7-day average (1.0 = baseline).
        price_variance: Proxy for price uncertainty (e.g., bid-ask spread).

    Returns:
        PMRegimeClassification with regime, confidence, threshold, and scale.
    """
    # Rule 1 (highest priority): closing soon — heightened edge requirement
    if hours_to_close < 24:
        regime = PMRegimeState.PRE_RESOLUTION
        confidence = 0.95

    # Rule 2: freshly created — market still price-discovering
    elif hours_since_created < 48:
        regime = PMRegimeState.DISCOVERY
        confidence = 0.80

    # Rule 3: abnormal volume spike — news-driven repricing
    elif volume_spike_ratio > 3.0:
        regime = PMRegimeState.NEWS_CATALYST
        confidence = 0.75

    # Rule 4: low variance — market has reached equilibrium
    elif price_variance < 0.02:
        regime = PMRegimeState.CONSENSUS
        confidence = 0.85

    # Rule 5 (fallback): elevated variance without a clear catalyst
    else:
        regime = PMRegimeState.SHARP_DISAGREEMENT
        confidence = 0.65

    return PMRegimeClassification(
        regime=regime,
        confidence=confidence,
        edge_threshold_pct=PM_REGIME_THRESHOLDS[regime],
        scale=PM_REGIME_SCALE[regime],
    )
