"""RED stubs: FillHazardModel + SpreadDepthMetrics. MICRO-01."""
import pytest
from sharpedge_venue_adapters.microstructure import (  # ImportError until Wave 4
    fill_hazard_estimate,
    SpreadDepthMetrics,
    compute_spread_depth,
)


def test_at_the_market_fill_prob_high():
    """Limit price == best ask -> near-certain fill (>= 0.90)."""
    p = fill_hazard_estimate(
        limit_price_prob=0.52,
        best_ask_prob=0.52,
        depth_at_price=200,
        ttr_hours=24.0,
        taker_fee_rate=0.07,
    )
    assert p >= 0.90


def test_far_passive_fill_prob_low():
    """Limit price 5 cents below best ask -> very low fill probability."""
    p = fill_hazard_estimate(
        limit_price_prob=0.47,
        best_ask_prob=0.52,
        depth_at_price=50,
        ttr_hours=24.0,
        taker_fee_rate=0.07,
    )
    assert p < 0.30


def test_near_resolution_reduces_fill_prob():
    """Low TTR (0.5 hours) should reduce fill prob vs same order with 24h TTR."""
    p_long = fill_hazard_estimate(0.50, 0.52, 100, ttr_hours=24.0, taker_fee_rate=0.07)
    p_short = fill_hazard_estimate(0.50, 0.52, 100, ttr_hours=0.5, taker_fee_rate=0.07)
    assert p_short < p_long


def test_fill_hazard_output_in_range():
    p = fill_hazard_estimate(0.50, 0.52, 100, ttr_hours=4.0, taker_fee_rate=0.07)
    assert 0.0 <= p <= 1.0


def test_compute_spread_depth_returns_metrics(mock_orderbook):
    metrics = compute_spread_depth(mock_orderbook)
    assert isinstance(metrics, SpreadDepthMetrics)
    assert metrics.spread_prob > 0
    assert metrics.depth_at_best_ask > 0
