"""RED test stubs for ablation backtest (Phase 13 Wave 0).

All 3 tests must FAIL with NotImplementedError until Plan 02 implements
compute_ablation_report(). Zero syntax errors and zero ImportErrors.

Tests are written in GREEN assertion form so Plan 02 requires zero test
file changes.
"""

from __future__ import annotations

from sharpedge_venue_adapters.ablation import compute_ablation_report

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------


def _make_resolved_markets(
    category: str,
    model_probs: list[float],
    market_prices: list[float],
    resolved_yes_values: list[int],
) -> list[dict]:
    """Build resolved_markets rows for a single category."""
    return [
        {
            "category": category,
            "market_price": mp,
            "resolved_yes": ry,
            "model_prob": mp_model,
        }
        for mp_model, mp, ry in zip(model_probs, market_prices, resolved_yes_values, strict=False)
    ]


# ---------------------------------------------------------------------------
# Test 1: per-category delta computation
# ---------------------------------------------------------------------------


def test_ablation_computes_per_category_delta(tmp_path):
    """compute_ablation_report() returns per-category delta = model_edge - fallback_edge."""
    # For crypto: model bets YES at 0.70 when market is 0.50; resolved=YES
    # fee_rate=0.05 applied to both edges
    # model_edge (gross) = model_prob - market_price = 0.70 - 0.50 = 0.20
    # fallback_edge (gross) = 0.0 (market price IS the fallback — no edge)
    # net edges: model = 0.20 * (1 - 0.05) = 0.19, fallback = 0.0 * (1 - 0.05) = 0.0
    # delta ≈ 0.19
    rows = _make_resolved_markets(
        category="crypto",
        model_probs=[0.70, 0.65],
        market_prices=[0.50, 0.48],
        resolved_yes_values=[1, 1],
    )
    result = compute_ablation_report(rows, tmp_path, fee_rate=0.05, threshold_pct=1.5)
    assert "categories" in result
    assert "crypto" in result["categories"]
    crypto = result["categories"]["crypto"]
    assert "delta" in crypto
    assert crypto["delta"] > 0.0


# ---------------------------------------------------------------------------
# Test 2: overall pass when all deltas above threshold
# ---------------------------------------------------------------------------


def test_ablation_pass_threshold(tmp_path):
    """Report passes when all category deltas >= 0.0% and overall delta >= 1.5%."""
    # Build one row per category — all with strong positive model edge
    rows = []
    for cat in ("crypto", "economic", "entertainment", "political", "weather"):
        rows.extend(
            _make_resolved_markets(
                category=cat,
                model_probs=[0.75, 0.70],
                market_prices=[0.50, 0.48],
                resolved_yes_values=[1, 1],
            )
        )
    result = compute_ablation_report(rows, tmp_path, fee_rate=0.05, threshold_pct=1.5)
    assert result["passed"] is True
    for cat_data in result["categories"].values():
        assert cat_data["passed"] is True


# ---------------------------------------------------------------------------
# Test 3: fail when any category has negative delta
# ---------------------------------------------------------------------------


def test_ablation_fail_negative_category(tmp_path):
    """Report fails when any category delta < 0.0%."""
    # weather category has model worse than fallback (model=0.30 on market=0.60)
    rows = []
    for cat in ("crypto", "economic", "entertainment", "political"):
        rows.extend(
            _make_resolved_markets(
                category=cat,
                model_probs=[0.70, 0.68],
                market_prices=[0.50, 0.48],
                resolved_yes_values=[1, 1],
            )
        )
    # weather: model_prob < market_price → negative delta
    rows.extend(
        _make_resolved_markets(
            category="weather",
            model_probs=[0.30, 0.35],
            market_prices=[0.60, 0.62],
            resolved_yes_values=[0, 0],
        )
    )
    result = compute_ablation_report(rows, tmp_path, fee_rate=0.05, threshold_pct=1.5)
    assert result["passed"] is False
    assert result["categories"]["weather"]["passed"] is False
