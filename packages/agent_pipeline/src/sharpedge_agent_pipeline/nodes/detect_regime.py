"""detect_regime node: classifies the betting market regime.

Calls classify_regime() from sharpedge_analytics.regime. No LLM, no network.
Appends quality_warnings if confidence < 0.5.
Under 60 lines.
"""
from __future__ import annotations

import logging

from sharpedge_analytics.regime import classify_regime, RegimeClassification

logger = logging.getLogger("sharpedge.agent.detect_regime")

_LOW_CONFIDENCE_THRESHOLD = 0.5


def detect_regime(state: dict) -> dict:
    """Classify the betting market regime from regime_inputs.

    Args:
        state: BettingAnalysisState with regime_inputs set by fetch_context.

    Returns:
        Partial state dict with regime_result and optionally quality_warnings.
    """
    regime_inputs: dict = state.get("regime_inputs") or {}

    try:
        result: RegimeClassification = classify_regime(
            ticket_pct=regime_inputs.get("ticket_pct", 0.5),
            handle_pct=regime_inputs.get("handle_pct", 0.5),
            line_move_pts=regime_inputs.get("line_move_pts", 0.0),
            move_velocity=regime_inputs.get("move_velocity", 0.0),
            book_alignment=regime_inputs.get("book_alignment", 0.5),
        )
    except Exception as exc:
        logger.warning("classify_regime failed: %s", exc)
        return {
            "regime_result": None,
            "quality_warnings": [f"detect_regime failed: {exc}"],
        }

    output: dict = {"regime_result": result}

    if result.confidence < _LOW_CONFIDENCE_THRESHOLD:
        output["quality_warnings"] = [
            f"Low regime confidence ({result.confidence:.2f}) — treat regime signal with caution"
        ]

    return output
