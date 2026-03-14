"""Failing test stubs for QUANT-01: AlphaComposer / compose_alpha."""
import pytest


def test_compose_alpha_premium():
    """High edge_score + favorable regime returns PREMIUM badge."""
    from sharpedge_models.alpha import compose_alpha
    result = compose_alpha(edge_score=0.80, regime_scale=1.3, survival_prob=0.97, confidence_mult=1.0)
    assert result.quality_badge == "PREMIUM"


def test_edge_floor():
    """edge_score < 0.05 forces SPECULATIVE regardless of multipliers."""
    from sharpedge_models.alpha import compose_alpha
    result = compose_alpha(edge_score=0.04, regime_scale=1.4, survival_prob=0.97, confidence_mult=1.1)
    assert result.quality_badge == "SPECULATIVE"


def test_compose_alpha_returns_betting_alpha():
    """compose_alpha returns a BettingAlpha dataclass with alpha field."""
    from sharpedge_models.alpha import compose_alpha, BettingAlpha
    result = compose_alpha(edge_score=0.60, regime_scale=1.0, survival_prob=0.95, confidence_mult=1.0)
    assert isinstance(result, BettingAlpha)
    assert 0.0 <= result.alpha <= 1.0
