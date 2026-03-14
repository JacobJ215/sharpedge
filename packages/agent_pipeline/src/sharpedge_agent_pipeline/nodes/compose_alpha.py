"""compose_alpha node: computes composite BettingAlpha from ev + mc signals.

Calls compose_alpha() from sharpedge_models.alpha. No LLM, no network.
Under 80 lines.
"""
from __future__ import annotations

import logging
from pathlib import Path

from sharpedge_analytics.regime import REGIME_SCALE, RegimeState
from sharpedge_models.alpha import compose_alpha as _compose_alpha, BettingAlpha
try:
    from sharpedge_models.calibration_store import CalibrationStore, DEFAULT_CALIBRATION_PATH
except ImportError:
    CalibrationStore = None  # type: ignore[assignment,misc]
    DEFAULT_CALIBRATION_PATH = Path("models/calibration_store.joblib")  # type: ignore[assignment]

logger = logging.getLogger("sharpedge.agent.compose_alpha")

_CAL_STORE: "CalibrationStore | None" = None


def _get_cal_store(store_path: Path) -> "CalibrationStore":
    """Lazy singleton — loads CalibrationStore once per process, not on every call.

    Avoids a joblib disk read on every alpha computation.
    """
    global _CAL_STORE
    if _CAL_STORE is None:
        _CAL_STORE = CalibrationStore(store_path)
    return _CAL_STORE


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

    # confidence_mult: sourced from CalibrationStore per sport (Phase 5)
    sport: str = state.get("game_context", {}).get("sport", "").lower()
    try:
        _cal_store = _get_cal_store(DEFAULT_CALIBRATION_PATH)
        confidence_mult: float = _cal_store.get_confidence_mult(sport)
    except Exception:
        confidence_mult = 1.0  # graceful fallback

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
