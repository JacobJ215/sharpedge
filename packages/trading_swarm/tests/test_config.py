"""Tests for TradingConfig loader."""

import pytest
from sharpedge_trading.config import _BOUNDS, _DEFAULTS, TradingConfig, _clamp


def test_defaults_are_within_bounds():
    for key, default in _DEFAULTS.items():
        lo, hi = _BOUNDS[key]
        assert lo <= default <= hi, f"{key} default {default} outside bounds [{lo}, {hi}]"


def test_from_dict_uses_defaults_for_missing_keys():
    config = TradingConfig.from_dict({})
    assert config.confidence_threshold == _DEFAULTS["confidence_threshold"]
    assert config.kelly_fraction == _DEFAULTS["kelly_fraction"]
    assert config.max_category_exposure == _DEFAULTS["max_category_exposure"]
    assert config.max_total_exposure == _DEFAULTS["max_total_exposure"]
    assert config.daily_loss_limit == _DEFAULTS["daily_loss_limit"]
    assert config.min_liquidity == _DEFAULTS["min_liquidity"]
    assert config.min_edge == _DEFAULTS["min_edge"]


def test_from_dict_applies_valid_values():
    config = TradingConfig.from_dict(
        {
            "confidence_threshold": "0.05",
            "kelly_fraction": "0.30",
        }
    )
    assert config.confidence_threshold == 0.05
    assert config.kelly_fraction == 0.30


def test_clamp_enforces_lower_bound():
    result = _clamp("confidence_threshold", 0.001)
    assert result == 0.01


def test_clamp_enforces_upper_bound():
    result = _clamp("kelly_fraction", 0.99)
    assert result == 0.50


def test_clamp_passes_through_valid_value():
    result = _clamp("confidence_threshold", 0.05)
    assert result == 0.05


def test_from_dict_clamps_out_of_bounds_value():
    config = TradingConfig.from_dict({"kelly_fraction": "0.99"})
    assert config.kelly_fraction == 0.50


def test_from_dict_handles_invalid_non_numeric_value():
    config = TradingConfig.from_dict({"confidence_threshold": "not-a-number"})
    assert config.confidence_threshold == _DEFAULTS["confidence_threshold"]


def test_defaults_factory_returns_all_defaults():
    config = TradingConfig.defaults()
    for key, default in _DEFAULTS.items():
        assert getattr(config, key) == default


def test_config_is_frozen():
    config = TradingConfig.defaults()
    with pytest.raises((AttributeError, TypeError)):
        config.kelly_fraction = 0.5  # type: ignore[misc]


def test_clamp_raises_for_unknown_key():
    with pytest.raises(KeyError, match="Unknown config key"):
        _clamp("nonexistent_key", 0.5)
