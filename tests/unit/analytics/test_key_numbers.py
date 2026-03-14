"""Failing test stubs for QUANT-04: Key number zone analysis."""
import pytest


def test_analyze_key_numbers_nfl_3():
    """NFL -3 returns crosses_key=False, key_frequency=0.152."""
    from sharpedge_analytics.key_numbers import analyze_key_numbers
    result = analyze_key_numbers(-3.0, "NFL")
    assert result.key_frequency == pytest.approx(0.152)
    assert result.crosses_key is False


def test_hook_detection():
    """NFL -2.5 (on hook) returns crosses_key=True."""
    from sharpedge_analytics.key_numbers import analyze_key_numbers
    result = analyze_key_numbers(-2.5, "NFL")
    assert result.crosses_key is True


def test_zone_analysis_fields():
    """analyze_key_numbers returns all required fields for QUANT-04."""
    from sharpedge_analytics.key_numbers import analyze_key_numbers
    result = analyze_key_numbers(-3.0, "NFL")
    assert hasattr(result, "key_frequency")
    assert hasattr(result, "value_adjustment")
    assert hasattr(result, "nearest_key")
    assert hasattr(result, "distance_to_key")
    assert hasattr(result, "crosses_key")
