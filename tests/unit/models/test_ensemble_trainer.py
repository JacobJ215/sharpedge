"""RED stubs for EnsembleManager — MODEL-01.

These tests will fail with ImportError until Plan 05-03 implements
packages/models/src/sharpedge_models/ensemble_trainer.py.
"""
import numpy as np
import pytest

from sharpedge_models.ensemble_trainer import EnsembleManager
from sharpedge_models.feature_assembler import GameFeatures


@pytest.fixture
def synthetic_training_data():
    """Synthetic X_by_domain and y for ensemble training (100 samples, 5 domains)."""
    rng = np.random.default_rng(42)
    X_by_domain = {
        "form": rng.random((100, 8)),
        "matchup": rng.random((100, 6)),
        "injury": rng.random((100, 4)),
        "sentiment": rng.random((100, 5)),
        "weather": rng.random((100, 3)),
    }
    y = rng.integers(0, 2, size=100).astype(float)
    return X_by_domain, y


@pytest.fixture
def synthetic_game_features():
    """Minimal GameFeatures object for predict_ensemble testing."""
    return GameFeatures(
        home_team="Chiefs",
        away_team="Raiders",
        sport="NFL",
        spread_line=-3.5,
        home_win_pct=0.62,
        away_win_pct=0.44,
        home_avg_points_scored=27.4,
        away_avg_points_scored=21.2,
        home_avg_points_allowed=18.8,
        away_avg_points_allowed=24.1,
        travel_penalty=0.0,
    )


def test_predict_ensemble_returns_dict(synthetic_training_data, synthetic_game_features):
    """EnsembleManager.predict_ensemble returns dict with all required probability keys."""
    X_by_domain, y = synthetic_training_data
    manager = EnsembleManager()
    manager.train(X_by_domain, y)
    result = manager.predict_ensemble(synthetic_game_features)

    assert isinstance(result, dict), f"Expected dict, got {type(result)}"
    required_keys = {
        "meta_prob",
        "form_prob",
        "matchup_prob",
        "injury_prob",
        "sentiment_prob",
        "weather_prob",
    }
    missing = required_keys - set(result.keys())
    assert not missing, f"predict_ensemble missing keys: {missing}"


def test_predict_ensemble_probability_range(synthetic_training_data, synthetic_game_features):
    """All probability values returned by predict_ensemble are in [0, 1]."""
    X_by_domain, y = synthetic_training_data
    manager = EnsembleManager()
    manager.train(X_by_domain, y)
    result = manager.predict_ensemble(synthetic_game_features)

    for key, value in result.items():
        assert isinstance(value, float), f"{key} should be float, got {type(value)}"
        assert 0.0 <= value <= 1.0, f"{key}={value} is outside [0, 1]"


def test_no_leakage_oof(synthetic_training_data):
    """OOF predictions have no row-overlap with any single base model's training fold.

    After training, oof_indices attribute stores fold assignments per model.
    For each fold k, the OOF rows used for meta-learner must NOT appear in
    model k's training set — verifying no data leakage.
    """
    X_by_domain, y = synthetic_training_data
    manager = EnsembleManager()
    manager.train(X_by_domain, y)

    # EnsembleManager must expose oof_indices: list[tuple[train_idx, val_idx]]
    assert hasattr(manager, "oof_indices"), (
        "EnsembleManager.train() must set self.oof_indices for leakage verification"
    )
    oof_indices = manager.oof_indices  # list of (train_idx, val_idx) per fold
    assert len(oof_indices) >= 2, "Expected at least 2 folds in oof_indices"

    for fold_i, (train_idx, val_idx) in enumerate(oof_indices):
        train_set = set(train_idx)
        val_set = set(val_idx)
        overlap = train_set & val_set
        assert not overlap, (
            f"Fold {fold_i}: train/val overlap of {len(overlap)} rows — data leakage detected"
        )


def test_train_produces_loadable_models(synthetic_training_data, synthetic_game_features):
    """After EnsembleManager.train(), predict_ensemble succeeds without error."""
    X_by_domain, y = synthetic_training_data
    manager = EnsembleManager()
    manager.train(X_by_domain, y)

    # Should not raise any exception
    result = manager.predict_ensemble(synthetic_game_features)
    assert result is not None, "predict_ensemble returned None after successful train()"
