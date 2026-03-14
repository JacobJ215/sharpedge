"""Tests for MLModelManager.predict_ensemble and BacktestResult.model_version.

TDD contract for Plan 05-03 Task 2:
- MLModelManager gains predict_ensemble() method
- BacktestResult gains model_version field
"""

from datetime import datetime, timezone

import pytest

from sharpedge_models.backtesting import BacktestResult
from sharpedge_models.ml_inference import GameFeatures, MLModelManager


# ---------------------------------------------------------------------------
# Task 2a: MLModelManager.predict_ensemble
# ---------------------------------------------------------------------------


def test_predict_ensemble_on_manager():
    """MLModelManager().predict_ensemble(sport, features) returns dict or None.

    Must not raise AttributeError — the method must exist on the class.
    When no ensemble model is loaded, returns None gracefully.
    """
    manager = MLModelManager()
    features = GameFeatures(
        home_team="Chiefs",
        away_team="Raiders",
        sport="nfl",
    )
    result = manager.predict_ensemble("nfl", features)
    # Without a trained model loaded, result should be None (not AttributeError)
    assert result is None or isinstance(result, dict), (
        f"predict_ensemble must return dict or None, got {type(result)}"
    )


# ---------------------------------------------------------------------------
# Task 2b: BacktestResult.model_version field
# ---------------------------------------------------------------------------


def test_backtest_result_has_model_version():
    """BacktestResult accepts model_version field without error."""
    result = BacktestResult(
        prediction_id="test_pred_001",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="nfl",
        predicted_probability=0.58,
        predicted_edge=3.2,
        odds=-110,
        outcome=None,
        closing_line=None,
        model_version="2026-03-14",
    )
    assert result.model_version == "2026-03-14"


def test_backtest_result_model_version_default():
    """BacktestResult.model_version defaults to empty string."""
    result = BacktestResult(
        prediction_id="test_pred_002",
        timestamp=datetime.now(timezone.utc),
        market_type="spread",
        sport="nfl",
        predicted_probability=0.52,
        predicted_edge=1.0,
        odds=-110,
        outcome=None,
        closing_line=None,
    )
    assert result.model_version == ""
