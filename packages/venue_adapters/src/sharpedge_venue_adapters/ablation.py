"""Ablation backtest helpers — compare fee-adjusted fallback vs trained-model edge.

Phase 13: ablation.py implementation (Plan 02 — GREEN phase).

Ablation report schema (data/ablation_report.json):
{
  "generated_at": "2026-03-20T12:00:00+00:00",
  "threshold_pct": 1.5,
  "categories": {
    "crypto":        {"model_edge": 0.041, "fallback_edge": 0.022, "delta": 0.019, "n_markets": 50, "passed": true},
    ...
  },
  "overall": {"model_edge": 0.037, "fallback_edge": 0.020, "delta": 0.017, "passed": true},
  "passed": true
}
"""
from __future__ import annotations

import joblib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sharpedge_venue_adapters.capital_gate import CATEGORIES


def compute_ablation_report(
    resolved_markets: list[dict],
    models_dir: Path,
    fee_rate: float = 0.05,
    threshold_pct: float = 1.5,
) -> dict:
    """Compute per-category and overall ablation report.

    Args:
        resolved_markets: List of dicts with keys: category, market_price,
                          resolved_yes (0 or 1). Optional key: model_prob
                          (pre-computed probability; used when no .joblib exists).
        models_dir: Directory containing {category}.joblib files.
        fee_rate: Kalshi fee rate applied to both model and fallback edges.
                  Default 0.05 (5%).
        threshold_pct: Minimum overall edge delta (%) for report.passed=True.
                       Also requires all category deltas >= 0.0%.

    Returns:
        Dict matching ablation report JSON schema.
    """
    # Group markets by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for m in resolved_markets:
        by_category[m["category"]].append(m)

    categories_result: dict[str, dict] = {}

    for cat in CATEGORIES:
        markets = by_category.get(cat, [])
        if not markets:
            categories_result[cat] = {
                "model_edge": 0.0,
                "fallback_edge": 0.0,
                "delta": 0.0,
                "n_markets": 0,
                "passed": True,
            }
            continue

        # Load model for this category if available
        model_path = models_dir / f"{cat}.joblib"
        model = joblib.load(model_path) if model_path.exists() else None

        model_edges: list[float] = []
        fallback_edges: list[float] = []

        for m in markets:
            market_price: float = m["market_price"]

            # Fallback baseline: always bet YES at market price.
            # Edge = (market_price - market_price) * (1 - fee_rate) = 0.
            # Represented as: edge = 0.0 per market (D-07).
            fallback_edge = 0.0
            fallback_edges.append(fallback_edge)

            # Model: use loaded model if available, else use model_prob from
            # row data, else fall back to market_price (zero edge).
            if model is not None:
                try:
                    prob = float(model.predict_proba([[market_price]])[0][1])
                except Exception:
                    prob = float(m.get("model_prob", market_price))
            else:
                prob = float(m.get("model_prob", market_price))

            # Edge = (model_prob - market_price) * (1 - fee_rate)
            model_edge_val = (prob - market_price) * (1 - fee_rate)
            model_edges.append(model_edge_val)

        mean_model_edge = sum(model_edges) / len(model_edges)
        mean_fallback_edge = sum(fallback_edges) / len(fallback_edges)
        delta = mean_model_edge - mean_fallback_edge

        categories_result[cat] = {
            "model_edge": round(mean_model_edge, 6),
            "fallback_edge": round(mean_fallback_edge, 6),
            "delta": round(delta, 6),
            "n_markets": len(markets),
            "passed": delta >= 0.0,  # D-09: every category >= 0.0%
        }

    # Compute overall averages (weighted by presence, not n_markets)
    active_cats = [c for c in CATEGORIES if categories_result[c]["n_markets"] > 0]
    if active_cats:
        overall_model = sum(categories_result[c]["model_edge"] for c in active_cats) / len(active_cats)
        overall_fallback = sum(categories_result[c]["fallback_edge"] for c in active_cats) / len(active_cats)
    else:
        overall_model = 0.0
        overall_fallback = 0.0

    overall_delta = overall_model - overall_fallback

    # Apply pass/fail threshold (D-09)
    all_categories_pass = all(categories_result[c]["passed"] for c in CATEGORIES)
    overall_passed = (overall_delta >= (threshold_pct / 100.0)) and all_categories_pass

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "threshold_pct": threshold_pct,
        "categories": categories_result,
        "overall": {
            "model_edge": round(overall_model, 6),
            "fallback_edge": round(overall_fallback, 6),
            "delta": round(overall_delta, 6),
            "passed": overall_passed,
        },
        "passed": overall_passed,
    }
