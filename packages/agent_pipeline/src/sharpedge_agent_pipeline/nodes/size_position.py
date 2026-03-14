"""size_position node: computes Kelly-based position size.

Uses half-Kelly formula: kelly = (edge / (1/win_prob - 1)) * 0.5
Clamps output to [0.005, 0.25]. No LLM, no network. Under 50 lines.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("sharpedge.agent.size_position")

_MIN_KELLY = 0.005
_MAX_KELLY = 0.25


def size_position(state: dict) -> dict:
    """Compute half-Kelly fraction from ev_result edge and win probability.

    Formula: kelly = (edge_decimal / (1/win_prob - 1)) * 0.5
    Clamped to [0.005, 0.25] to prevent over-betting or trivial positions.

    Args:
        state: BettingAnalysisState with ev_result set.

    Returns:
        Partial state dict with kelly_fraction (float, 0.005–0.25).
    """
    ev_result: dict = state.get("ev_result") or {}

    # edge is stored as percentage points (e.g., 3.5 means 3.5%)
    edge_pct: float = ev_result.get("edge", 0.0)
    edge: float = edge_pct / 100.0

    model_prob_pct: float = ev_result.get("model_prob", 52.0)
    win_prob: float = model_prob_pct / 100.0

    # Avoid division by zero; no position if win_prob is 0 or 1
    if win_prob <= 0.0 or win_prob >= 1.0 or edge <= 0.0:
        return {"kelly_fraction": _MIN_KELLY}

    try:
        # b = decimal odds - 1 = win_amount per unit staked = (1/win_prob - 1) approx
        b = (1.0 / win_prob) - 1.0
        kelly_full = edge / b
        kelly_half = kelly_full * 0.5
        kelly_fraction = max(_MIN_KELLY, min(kelly_half, _MAX_KELLY))
    except ZeroDivisionError:
        kelly_fraction = _MIN_KELLY

    return {"kelly_fraction": kelly_fraction}
