"""RED stubs for PM regime classifier — covers PM-03.

These tests will fail with ImportError until pm_regime module is
created in Wave 1. All tests are pure/synchronous.
"""

from sharpedge_analytics.pm_regime import (
    classify_pm_regime,
    PMRegimeState,
    PMRegimeClassification,
    PM_REGIME_THRESHOLDS,
)


def test_pre_resolution_when_hours_to_close_lt_24():
    """hours_to_close=12 → regime == PRE_RESOLUTION."""
    result = classify_pm_regime(
        hours_to_close=12,
        hours_since_created=200,
        volume_spike_ratio=1.0,
        price_variance=0.05,
    )
    assert isinstance(result, PMRegimeClassification)
    assert result.regime == PMRegimeState.PRE_RESOLUTION


def test_discovery_when_market_age_lt_48h():
    """hours_to_close=72, hours_since_created=24 → regime == DISCOVERY."""
    result = classify_pm_regime(
        hours_to_close=72,
        hours_since_created=24,
        volume_spike_ratio=1.0,
        price_variance=0.05,
    )
    assert result.regime == PMRegimeState.DISCOVERY


def test_news_catalyst_on_volume_spike():
    """volume_spike_ratio=5.0 → regime == NEWS_CATALYST (not PRE_RESOLUTION or DISCOVERY)."""
    result = classify_pm_regime(
        hours_to_close=120,
        hours_since_created=200,
        volume_spike_ratio=5.0,
        price_variance=0.05,
    )
    assert result.regime == PMRegimeState.NEWS_CATALYST


def test_consensus_on_low_variance():
    """price_variance=0.01, no spike → regime == CONSENSUS."""
    result = classify_pm_regime(
        hours_to_close=120,
        hours_since_created=200,
        volume_spike_ratio=1.0,
        price_variance=0.01,
    )
    assert result.regime == PMRegimeState.CONSENSUS


def test_sharp_disagreement_default():
    """High variance, no spike, not young, not closing → regime == SHARP_DISAGREEMENT."""
    result = classify_pm_regime(
        hours_to_close=120,
        hours_since_created=200,
        volume_spike_ratio=1.0,
        price_variance=0.25,
    )
    assert result.regime == PMRegimeState.SHARP_DISAGREEMENT


def test_discovery_threshold_is_2_pct():
    """DISCOVERY regime has edge_threshold_pct == 2.0."""
    result = classify_pm_regime(
        hours_to_close=72,
        hours_since_created=24,
        volume_spike_ratio=1.0,
        price_variance=0.05,
    )
    assert result.regime == PMRegimeState.DISCOVERY
    assert result.edge_threshold_pct == 2.0


def test_pre_resolution_threshold_is_5_pct():
    """PRE_RESOLUTION regime has edge_threshold_pct == 5.0."""
    result = classify_pm_regime(
        hours_to_close=12,
        hours_since_created=200,
        volume_spike_ratio=1.0,
        price_variance=0.05,
    )
    assert result.regime == PMRegimeState.PRE_RESOLUTION
    assert result.edge_threshold_pct == 5.0


def test_priority_pre_resolution_beats_discovery():
    """hours_to_close=12, hours_since_created=24 → PRE_RESOLUTION (not DISCOVERY)."""
    result = classify_pm_regime(
        hours_to_close=12,
        hours_since_created=24,
        volume_spike_ratio=1.0,
        price_variance=0.05,
    )
    assert result.regime == PMRegimeState.PRE_RESOLUTION
