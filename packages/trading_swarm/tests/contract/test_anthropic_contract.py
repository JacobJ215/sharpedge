"""Contract tests for Anthropic/Claude API — verifies LLMCalibrator works end-to-end."""
import os
import pytest


@pytest.fixture(scope="module")
def calibrator(require_anthropic):
    from sharpedge_trading.signals.llm_calibrator import LLMCalibrator
    return LLMCalibrator(api_key=os.environ["ANTHROPIC_API_KEY"])


def test_calibrate_returns_float_in_range(calibrator):
    """calibrate() returns a float in [0.05, 0.95]."""
    result = calibrator.calibrate(
        base_prob=0.55,
        narrative="Strong economic data suggests YES outcome is likely. Multiple indicators align.",
    )
    assert isinstance(result, float), f"Expected float, got {type(result)}"
    assert 0.05 <= result <= 0.95, f"Result {result} out of expected range [0.05, 0.95]"


def test_calibrate_stays_within_10pct_of_base(calibrator):
    """calibrate() never adjusts more than ±10% from base_prob."""
    base = 0.50
    result = calibrator.calibrate(
        base_prob=base,
        narrative="Highly bullish signals across all sources. Extremely confident YES.",
    )
    assert abs(result - base) <= 0.10 + 1e-6, (
        f"Adjustment {abs(result - base):.4f} exceeds ±0.10 cap"
    )


def test_calibrate_neutral_narrative_unchanged(calibrator):
    """Neutral narrative should return close to base_prob."""
    base = 0.48
    result = calibrator.calibrate(
        base_prob=base,
        narrative="No clear signals. Market is balanced. Uncertain outcome.",
    )
    # Allow up to 3% drift for a neutral narrative
    assert abs(result - base) <= 0.03 + 1e-6, (
        f"Neutral narrative changed base by {abs(result - base):.4f}"
    )


def test_calibrate_falls_back_on_empty_api_key():
    """calibrate() returns base_prob unchanged when API key is missing."""
    from sharpedge_trading.signals.llm_calibrator import LLMCalibrator
    calibrator_no_key = LLMCalibrator(api_key="")
    base = 0.60
    result = calibrator_no_key.calibrate(base, "Some narrative")
    assert result == base, "Should return base_prob when API key is missing"
