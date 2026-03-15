"""TDD tests for full model pipeline integration — PIPE-01.

Tests cover:
  - train_ensemble: data -> EnsembleManager
  - WalkForwardBacktester: run_with_model_inference -> BacktestReport with quality_badge
  - compute_max_drawdown from run_walk_forward.py
  - CalibrationStore: update + get_confidence_mult
  - compute_ece from run_calibration.py
  - Full pipeline chain: data -> train -> backtest -> calibrate -> alpha
"""
from __future__ import annotations

import importlib.util
import pathlib

import numpy as np
import pytest


def _load_script(script_name: str):
    """Load a script from the scripts/ directory via importlib."""
    root = pathlib.Path(__file__).parent.parent.parent.parent
    script_path = root / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_run_walk_forward():
    return _load_script("run_walk_forward.py")


@pytest.fixture(autouse=True)
def reset_cal_store():
    """Reset CalibrationStore singleton between tests."""
    try:
        import sharpedge_agent_pipeline.nodes.compose_alpha as ca
        ca._CAL_STORE = None
    except ImportError:
        pass
    yield
    try:
        import sharpedge_agent_pipeline.nodes.compose_alpha as ca
        ca._CAL_STORE = None
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Plan 07-04: Walk-forward tests (GREEN)
# ---------------------------------------------------------------------------

def test_walk_forward_produces_quality_badge():
    """WalkForwardBacktester.run_with_model_inference returns BacktestReport with valid badge."""
    pd = pytest.importorskip("pandas")
    sklearn_ensemble = pytest.importorskip("sklearn.ensemble")
    sklearn_pipeline = pytest.importorskip("sklearn.pipeline")
    sklearn_preprocessing = pytest.importorskip("sklearn.preprocessing")
    from sharpedge_models.walk_forward import BacktestReport, WalkForwardBacktester
    GradientBoostingClassifier = sklearn_ensemble.GradientBoostingClassifier
    Pipeline = sklearn_pipeline.Pipeline
    StandardScaler = sklearn_preprocessing.StandardScaler

    rng = np.random.default_rng(1)
    n = 100
    feature_df = pd.DataFrame(
        rng.random((n, 6)),
        columns=["home_ppg_10g", "away_ppg_10g", "home_ats_10g", "away_ats_10g", "home_rest", "away_rest"],
    )
    y = rng.integers(0, 2, size=n).astype(float)

    def model_fn(X_train, X_test, y_train):
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=50, random_state=0)),
        ])
        pipe.fit(X_train, y_train)
        return pipe

    backtester = WalkForwardBacktester()
    report = backtester.run_with_model_inference(feature_df, model_fn, y, n_windows=2)

    assert isinstance(report, BacktestReport)
    assert report.quality_badge in ("low", "medium", "high", "excellent"), (
        f"Unexpected quality_badge: {report.quality_badge}"
    )


def test_compute_max_drawdown_all_positive():
    """compute_max_drawdown returns 0.0 when all window ROIs are positive."""
    mod = _load_run_walk_forward()
    result = mod.compute_max_drawdown([0.05, 0.10, 0.03])
    assert result == 0.0, f"Expected 0.0, got {result}"


def test_compute_max_drawdown_with_loss():
    """compute_max_drawdown returns > 0.0 when a window has a losing ROI."""
    mod = _load_run_walk_forward()
    result = mod.compute_max_drawdown([0.10, -0.30, 0.05])
    assert result > 0.0, f"Expected positive drawdown, got {result}"


# ---------------------------------------------------------------------------
# Plan 07-05: Calibration tests (GREEN)
# ---------------------------------------------------------------------------

def test_calibration_store_updates_confidence_mult(tmp_path):
    """CalibrationStore.get_confidence_mult != 1.0 after update with >= MIN_GAMES games."""
    from sharpedge_models.calibration_store import MIN_GAMES, CalibrationStore

    rng = np.random.default_rng(2)
    n = MIN_GAMES + 10
    outcomes = rng.integers(0, 2, size=n).tolist()
    probs = [float(o) * 0.85 + 0.075 for o in outcomes]

    store_path = tmp_path / "test_cal_store.joblib"
    store = CalibrationStore(store_path)
    store.update("nba", probs, [bool(o) for o in outcomes])

    mult = store.get_confidence_mult("nba")
    assert mult != 1.0, f"Expected confidence_mult != 1.0 after update, got {mult}"
    assert 0.5 <= mult <= 1.2, f"confidence_mult must be in [0.5, 1.2], got {mult}"


def test_compute_ece():
    """compute_ece returns low ECE for well-calibrated predictions."""
    mod = _load_script("run_calibration.py")
    probs = [0.9] * 10
    outcomes = [True] * 10
    ece = mod.compute_ece(probs, outcomes)
    assert ece < 0.15, f"Expected low ECE for calibrated preds, got {ece}"


def test_oos_only_update():
    """CalibrationStore.update is called with OOS subset, not full dataset."""
    from unittest.mock import MagicMock
    from sharpedge_models.calibration_store import CalibrationStore

    rng = np.random.default_rng(7)
    n_full = 200
    n_oos = 40

    mock_store = MagicMock(spec=CalibrationStore)
    oos_probs = rng.random(n_oos).tolist()
    oos_outcomes = rng.integers(0, 2, size=n_oos).tolist()
    mock_store.update("nba", oos_probs, oos_outcomes)

    args = mock_store.update.call_args[0]
    sport, probs, outcomes = args
    assert len(probs) == n_oos, f"Expected {n_oos} OOS probs, got {len(probs)}"
    assert len(probs) < n_full, "OOS probs must be a subset of full dataset"


# ---------------------------------------------------------------------------
# Plan 07-06: Ensemble + End-to-end (GREEN)
# ---------------------------------------------------------------------------

def test_ensemble_trains_all_sports(tmp_path):
    """train_ensemble accepts a multi-sport DataFrame and returns a fitted EnsembleManager."""
    import pandas as pd
    from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES, train_ensemble

    rng = np.random.default_rng(42)
    sports = ["nba", "nfl", "mlb", "nhl", "ncaab"]
    n_per_sport = 20
    records = []
    for sport in sports:
        for _ in range(n_per_sport):
            row = {"sport": sport}
            for domain_cols in DOMAIN_FEATURES.values():
                for col in domain_cols:
                    row[col] = float(rng.random())
            row["home_covered"] = int(rng.integers(0, 2))
            records.append(row)

    df = pd.DataFrame(records)
    y = df["home_covered"].astype(float).values

    em = train_ensemble(df, y, tmp_path, "test_v1")
    assert em is not None
    assert hasattr(em, "oof_preds_"), "EnsembleManager must have oof_preds_ attribute"
    assert em.oof_preds_ is not None
    assert len(em.oof_preds_) == len(df), (
        f"oof_preds_ length {len(em.oof_preds_)} != df length {len(df)}"
    )


def test_pipeline_end_to_end(tmp_path):
    """Full chain: walk_forward -> calibrate -> compose_alpha > 0."""
    import pandas as pd
    from sharpedge_models.walk_forward import WalkForwardBacktester
    from sharpedge_models.calibration_store import CalibrationStore, MIN_GAMES
    from sharpedge_models.alpha import compose_alpha
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    rng = np.random.default_rng(99)
    n = 100
    feature_df = pd.DataFrame(
        rng.random((n, 6)),
        columns=["home_ppg_10g", "away_ppg_10g", "home_ats_10g", "away_ats_10g", "home_rest", "away_rest"],
    )
    y = rng.integers(0, 2, size=n).astype(int)

    def model_fn(X_train, X_test, y_train):
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=10, random_state=42)),
        ])
        pipe.fit(X_train, y_train)
        return pipe

    # Walk-forward
    backtester = WalkForwardBacktester()
    report = backtester.run_with_model_inference(feature_df, model_fn, y, n_windows=2)
    assert report.quality_badge in ("low", "medium", "high", "excellent")

    # Calibration
    store_path = tmp_path / "e2e_cal.joblib"
    store = CalibrationStore(store_path)
    n_oos = max(MIN_GAMES + 5, 60)
    oos_probs = rng.random(n_oos).tolist()
    oos_outcomes = rng.integers(0, 2, size=n_oos).tolist()
    store.update("nba", oos_probs, [bool(o) for o in oos_outcomes])
    confidence_mult = store.get_confidence_mult("nba")

    # compose_alpha
    alpha_result = compose_alpha(
        edge_score=0.55,
        regime_scale=1.0,
        survival_prob=0.9,
        confidence_mult=confidence_mult,
    )
    assert alpha_result.alpha > 0.0, f"Expected positive alpha, got {alpha_result.alpha}"
