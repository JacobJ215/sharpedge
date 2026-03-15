#!/usr/bin/env python3
"""Train ML models for spread and totals prediction.

This script trains gradient boosting models on historical betting data
to predict:
1. Spread outcomes (home team covers or not)
2. Totals outcomes (over or under)

Models are calibrated using Platt scaling to output well-calibrated
probabilities that can be used for EV calculations.

Output:
- data/models/{sport}_spread_model.joblib
- data/models/{sport}_totals_model.joblib
- data/models/{sport}_spread_metrics.json / {sport}_totals_metrics.json
- data/models/all_model_metrics.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib

# Directories
DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"

SUPPORTED_SPORTS = ["nfl", "nba", "ncaab", "mlb", "nhl"]


def load_training_data(sport: str) -> pd.DataFrame | None:
    """Load processed training data."""
    filepath = PROCESSED_DIR / f"{sport}_training.parquet"

    if not filepath.exists():
        print(f"Training data not found: {filepath}")
        return None

    df = pd.read_parquet(filepath)
    print(f"Loaded {len(df)} rows from {filepath}")
    return df


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    """Get list of feature columns for training."""
    # Exclude target and metadata columns
    exclude_patterns = [
        "game_date",
        "season",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "total_points",
        "point_diff",
        "spread_result",
        "total_result",
        "home_covered",
        "went_over",
        "spread_line",
        "total_line",
    ]

    features = []
    for col in df.columns:
        if col not in exclude_patterns and df[col].dtype in [
            np.float64,
            np.int64,
            np.bool_,
        ]:
            features.append(col)

    return features


def prepare_spread_data(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]] | None:
    """Prepare data for spread model training."""
    if "home_covered" not in df.columns:
        print("No spread target column found")
        return None

    # Get features
    feature_cols = get_feature_columns(df)
    if not feature_cols:
        print("No feature columns found")
        return None

    # Filter to rows with valid target and features
    valid_mask = df["home_covered"].notna()
    for col in feature_cols:
        valid_mask &= df[col].notna()

    df_valid = df[valid_mask].copy()
    print(f"Valid rows for spread training: {len(df_valid)}")

    X = df_valid[feature_cols]
    y = df_valid["home_covered"].astype(int)

    return X, y, feature_cols


def prepare_totals_data(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]] | None:
    """Prepare data for totals model training."""
    if "went_over" not in df.columns:
        print("No totals target column found")
        return None

    feature_cols = get_feature_columns(df)
    if not feature_cols:
        print("No feature columns found")
        return None

    valid_mask = df["went_over"].notna()
    for col in feature_cols:
        valid_mask &= df[col].notna()

    df_valid = df[valid_mask].copy()
    print(f"Valid rows for totals training: {len(df_valid)}")

    X = df_valid[feature_cols]
    y = df_valid["went_over"].astype(int)

    return X, y, feature_cols


def train_calibrated_model(
    X: pd.DataFrame, y: pd.Series, model_name: str, n_splits: int = 5,
) -> tuple[Any, dict]:
    """Train a calibrated gradient boosting model.

    Uses time-series cross-validation to respect temporal ordering.
    Applies isotonic regression for probability calibration.
    """
    print(f"\nTraining {model_name} model...")
    print(f"  Features: {len(X.columns)}")
    print(f"  Samples: {len(X)}")
    print(f"  Target distribution: {y.mean():.3f} (positive class)")

    # Time series split (respects temporal order)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    X_arr = X.values

    def _gbm() -> GradientBoostingClassifier:
        return GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42,
        )

    # Embed StandardScaler inside the pipeline so it is fit only on the
    # training portion of each CV fold — prevents distributional leakage
    # across the temporal boundary of TimeSeriesSplit.
    pipeline = Pipeline([("scaler", StandardScaler()), ("clf", _gbm())])
    calibrated_model = CalibratedClassifierCV(
        pipeline, method="isotonic", cv=tscv,
    )
    calibrated_model.fit(X_arr, y)

    # Evaluate on last fold using a fold-local pipeline so reported metrics
    # are unbiased (scaler is fit only on that fold's training rows).
    splits = list(tscv.split(X_arr))
    train_idx, test_idx = splits[-1]
    eval_pipeline = Pipeline([("scaler", StandardScaler()), ("clf", _gbm())])
    eval_pipeline.fit(X_arr[train_idx], y.iloc[train_idx])
    X_test_fold = X_arr[test_idx]
    y_test = y.iloc[test_idx]

    y_pred = eval_pipeline.predict(X_test_fold)
    y_prob = eval_pipeline.predict_proba(X_test_fold)[:, 1]

    # Metrics
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "auc_roc": float(roc_auc_score(y_test, y_prob)),
        "brier_score": float(brier_score_loss(y_test, y_prob)),
        "log_loss": float(log_loss(y_test, y_prob)),
        "n_samples": len(X),
        "n_features": len(X.columns),
        "feature_names": list(X.columns),
        "trained_at": datetime.now().isoformat(),
    }

    print("\n  Results (last fold, leak-free):")
    print(f"    Accuracy: {metrics['accuracy']:.3f}")
    print(f"    AUC-ROC: {metrics['auc_roc']:.3f}")
    print(f"    Brier Score: {metrics['brier_score']:.4f}")
    print(f"    Log Loss: {metrics['log_loss']:.4f}")

    # Calibration analysis
    print("\n  Calibration Analysis:")
    prob_bins = [0, 0.3, 0.4, 0.5, 0.6, 0.7, 1.0]
    for i in range(len(prob_bins) - 1):
        mask = (y_prob >= prob_bins[i]) & (y_prob < prob_bins[i + 1])
        if mask.sum() > 0:
            actual_rate = y_test[mask].mean()
            predicted_avg = y_prob[mask].mean()
            print(
                f"    Predicted {prob_bins[i]:.1f}-{prob_bins[i+1]:.1f} "
                f"(avg {predicted_avg:.3f}): "
                f"Actual {actual_rate:.3f}, n={mask.sum()}"
            )

    # The scaler is embedded in the calibrated pipeline; return None as the
    # separate scaler so ml_inference.py passes raw features directly to the
    # model (which handles scaling internally).
    return (calibrated_model, None), metrics


def save_model(model_bundle: tuple, name: str, metrics: dict) -> None:
    """Save trained model and metadata."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    model_path = MODELS_DIR / f"{name}_model.joblib"
    joblib.dump(model_bundle, model_path)
    print(f"\nSaved model to {model_path}")

    # Save metrics
    metrics_path = MODELS_DIR / f"{name}_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics to {metrics_path}")


def train_sport_models(sport: str) -> dict[str, dict]:
    """Train all models for a sport."""
    print(f"\n{'=' * 60}")
    print(f"Training {sport.upper()} Models")
    print("=" * 60)

    df = load_training_data(sport)
    if df is None:
        return {}

    results = {}

    # Train spread model
    spread_data = prepare_spread_data(df)
    if spread_data is not None:
        X, y, features = spread_data
        model, metrics = train_calibrated_model(X, y, f"{sport}_spread")
        save_model(model, f"{sport}_spread", metrics)
        results["spread"] = metrics

    # Train totals model
    totals_data = prepare_totals_data(df)
    if totals_data is not None:
        X, y, features = totals_data
        model, metrics = train_calibrated_model(X, y, f"{sport}_totals")
        save_model(model, f"{sport}_totals", metrics)
        results["totals"] = metrics

    # Train ensemble model (MODEL-01) if spread target available
    if "home_covered" in df.columns:
        _train_ensemble_for_sport(df, sport)

    return results


def _train_ensemble_for_sport(df: "pd.DataFrame", sport: str) -> None:
    """Train the 5-domain stacking ensemble for a given sport.

    Validates that all DOMAIN_FEATURES columns exist in df before training.
    Appends to MODELS_DIR without removing existing single-model artifacts.
    """
    from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES, train_ensemble

    all_domain_cols = [col for cols in DOMAIN_FEATURES.values() for col in cols]
    missing_cols = [c for c in all_domain_cols if c not in df.columns]
    if missing_cols:
        print(
            f"  Zero-filling {len(missing_cols)} missing DOMAIN_FEATURES columns "
            f"for {sport}: {missing_cols[:5]}{'...' if len(missing_cols) > 5 else ''}"
        )
        for col in missing_cols:
            df[col] = 0.0

    valid_mask = df["home_covered"].notna()
    for col in all_domain_cols:
        valid_mask &= df[col].notna()

    df_valid = df[valid_mask].copy()
    if len(df_valid) < 10:
        print(f"  Skipping ensemble training: only {len(df_valid)} valid rows")
        return

    y_ens = df_valid["home_covered"].astype(int).values
    print(f"\nTraining {sport.upper()} ensemble model ({len(df_valid)} rows)...")

    trained_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    train_ensemble(df_valid, y_ens, models_dir=MODELS_DIR, model_version=trained_at)
    print(f"Ensemble trained: {trained_at}")


def main():
    """Main training function."""
    print("=" * 60)
    print("SharpEdge ML Model Training")
    print("=" * 60)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_results = {}

    for sport in SUPPORTED_SPORTS:
        sport_results = train_sport_models(sport)
        if sport_results:
            all_results[sport] = sport_results

    # Save combined metrics
    if all_results:
        combined_metrics_path = MODELS_DIR / "all_model_metrics.json"
        with open(combined_metrics_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nSaved combined metrics to {combined_metrics_path}")

    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)

    for sport, models in all_results.items():
        print(f"\n{sport.upper()}:")
        for model_type, metrics in models.items():
            print(f"  {model_type}:")
            print(f"    Accuracy: {metrics['accuracy']:.3f}")
            print(f"    AUC-ROC: {metrics['auc_roc']:.3f}")
            print(f"    Brier Score: {metrics['brier_score']:.4f}")

    if not all_results:
        print("\nNo models trained. Please process data first:")
        print("  1. python scripts/download_historical_data.py")
        print("  2. python scripts/process_historical_data.py")
        print("  3. python scripts/train_models.py")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
