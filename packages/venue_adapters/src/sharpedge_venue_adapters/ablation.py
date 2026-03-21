"""Ablation backtest helpers — compare fee-adjusted fallback vs trained-model edge.

Phase 13: ablation.py stub (Wave 0 — RED phase). All function bodies raise
NotImplementedError. Plan 02 replaces them with real implementations.

Ablation report schema (data/ablation_report.json):
{
  "generated_at": "2026-03-20T12:00:00+00:00",
  "threshold_pct": 1.5,
  "categories": {
    "crypto":        {"model_edge": 0.041, "fallback_edge": 0.022, "delta": 0.019, "passed": true},
    ...
  },
  "overall": {"model_edge": 0.037, "fallback_edge": 0.020, "delta": 0.017, "passed": true},
  "passed": true
}
"""
from __future__ import annotations

from pathlib import Path


def compute_ablation_report(
    resolved_markets: list[dict],
    models_dir: Path,
    fee_rate: float = 0.05,
    threshold_pct: float = 1.5,
) -> dict:
    """Compute per-category and overall ablation report.

    Args:
        resolved_markets: List of dicts with keys: category, market_price,
                          resolved_yes (0 or 1).
        models_dir: Directory containing {category}.joblib files.
        fee_rate: Kalshi fee rate applied to both model and fallback edges.
                  Default 0.05 (5%).
        threshold_pct: Minimum overall edge delta (%) for report.passed=True.
                       Also requires all category deltas >= 0.0%.

    Returns:
        Dict matching ablation report JSON schema.
    """
    raise NotImplementedError
