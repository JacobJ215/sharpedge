"""RED stub tests for PMResolutionPredictor — Phase 9 plan 01.

build_model_probs() returns {} in stub → tests asserting non-empty output are RED.
Tests asserting empty output (flag off, missing models) are GREEN.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from sharpedge_models.pm_resolution_predictor import (
    ENABLE_FLAG,
    PM_MODEL_DIR,
    PMResolutionPredictor,
)


# ---------------------------------------------------------------------------
# Sample market fixtures
# ---------------------------------------------------------------------------

CRYPTO_MARKETS = [
    {"market_id": "KXBTC-100K", "category": "crypto", "market_prob": 0.4},
    {"market_id": "KXETH-5K", "category": "crypto", "market_prob": 0.35},
]

POLITICAL_MARKETS = [
    {"market_id": "KXPOL-DEM24", "category": "political", "market_prob": 0.55},
]


# ---------------------------------------------------------------------------
# GREEN tests — correct safe-default behavior already implemented in stub
# ---------------------------------------------------------------------------

def test_flag_off_returns_empty(monkeypatch):
    """When ENABLE_PM_RESOLUTION_MODEL is unset, build_model_probs returns {}."""
    monkeypatch.delenv(ENABLE_FLAG, raising=False)
    predictor = PMResolutionPredictor()
    result = predictor.build_model_probs(CRYPTO_MARKETS)
    assert result == {}


def test_no_exceptions_on_missing_models(monkeypatch):
    """build_model_probs() with all models missing returns {} without raising."""
    monkeypatch.setenv(ENABLE_FLAG, "1")
    predictor = PMResolutionPredictor()
    # Stub always returns {} — no exception should propagate.
    result = predictor.build_model_probs(CRYPTO_MARKETS + POLITICAL_MARKETS)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# RED tests — will pass once plan 03 implementation is complete
# ---------------------------------------------------------------------------

def test_flag_on_missing_model_file_returns_empty_for_category(monkeypatch, tmp_path):
    """Flag on, no joblib file for 'crypto' → crypto markets absent from dict."""
    monkeypatch.setenv(ENABLE_FLAG, "1")
    predictor = PMResolutionPredictor()
    result = predictor.build_model_probs(CRYPTO_MARKETS)
    # Stub returns {} which satisfies "not in returned dict" — this is actually
    # already a passing assertion for the stub. Marking intent: real impl should
    # also exclude unmodeled categories.
    for market in CRYPTO_MARKETS:
        assert market["market_id"] not in result


def test_skipped_category_not_in_output(monkeypatch):
    """Category with no model artifact → market_ids absent from returned dict."""
    monkeypatch.setenv(ENABLE_FLAG, "1")
    predictor = PMResolutionPredictor()
    result = predictor.build_model_probs(POLITICAL_MARKETS)
    for market in POLITICAL_MARKETS:
        assert market["market_id"] not in result


def test_flag_on_with_model_returns_probabilities(monkeypatch, tmp_path):
    """Flag on, mock joblib load returns fitted model → dict[market_id, float] with probabilities in (0, 1).

    This test is RED in the stub because build_model_probs() always returns {}.
    Plan 03 will implement model loading and probability inference.
    """
    monkeypatch.setenv(ENABLE_FLAG, "1")

    mock_model = MagicMock()
    mock_model.predict_proba.return_value = [[0.4, 0.6], [0.35, 0.65]]

    predictor = PMResolutionPredictor()
    with patch("joblib.load", return_value=mock_model):
        result = predictor.build_model_probs(CRYPTO_MARKETS)

    # RED: stub returns {} but real impl should return non-empty dict.
    assert len(result) > 0, (
        "Expected non-empty probability dict when model is available — "
        "implement in plan 03."
    )
    for market_id, prob in result.items():
        assert 0.0 < prob < 1.0, f"Probability out of range for {market_id}: {prob}"
