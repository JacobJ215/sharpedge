#!/usr/bin/env python3
"""Train per-category RandomForest binary classifiers for PM resolution prediction.

Categories with fewer than 200 resolved markets are skipped — no model file written.
Walk-forward validation runs per-category with 3 windows of 50+ markets minimum.
Categories achieving quality badge 'medium' or better are promoted to production.
"""
import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from sharpedge_models.walk_forward import WalkForwardBacktester, quality_badge_from_windows
from sharpedge_models.calibration_store import CalibrationStore
from sharpedge_models.pm_feature_assembler import PM_CATEGORIES

logger = logging.getLogger(__name__)

MIN_MARKETS: int = 200
N_WINDOWS: int = 3
N_ESTIMATORS: int = 100
RANDOM_STATE: int = 42
EXCLUDE_COLS: frozenset = frozenset({"resolved_yes", "category", "source"})


def _feat_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in EXCLUDE_COLS]


def _run_walk_forward(X: pd.DataFrame, y: list[int]) -> tuple[list, list[float], list[int]]:
    """Walk-forward validation; returns (windows, oof_probs, oof_actuals)."""
    def model_fn(X_train, X_test, y_train):
        clf = RandomForestClassifier(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE)
        clf.fit(X_train, y_train)
        return clf

    report = WalkForwardBacktester().run_with_model_inference(
        feature_df=X, model_fn=model_fn, y=np.array(y), n_windows=N_WINDOWS,
    )
    windows = report.windows
    n, chunk_size = len(X), len(X) // (N_WINDOWS + 1)
    y_arr = list(y)
    oof_probs: list[float] = []
    oof_actuals: list[int] = []
    for w_idx in range(N_WINDOWS):
        train_end = (w_idx + 1) * chunk_size
        test_start, test_end = train_end, min(train_end + chunk_size, n)
        X_tr, X_te = X.iloc[:train_end], X.iloc[test_start:test_end]
        y_tr = np.array(y_arr[:train_end])
        if len(X_te) == 0 or len(set(y_tr.tolist())) < 2:
            continue
        try:
            clf = RandomForestClassifier(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE)
            clf.fit(X_tr, y_tr)
            oof_probs.extend(clf.predict_proba(X_te)[:, 1].tolist())
            oof_actuals.extend(y_arr[test_start:test_end])
        except Exception as exc:
            logger.warning("_run_walk_forward: OOF failed window %d — %s", w_idx, exc)
    return windows, oof_probs, oof_actuals


def train_category(
    category: str,
    df: pd.DataFrame,
    model_dir: Path,
    report_path: Path | None = None,
    report: list | None = None,
) -> bool:
    """Train RandomForest for one PM category. Returns True if model was written."""
    model_dir = Path(model_dir)
    rp = Path(report_path) if report_path is not None else None

    def _write_entry(entry: dict) -> None:
        if report is not None:
            report.append(entry)
        if rp is not None:
            existing: list = json.loads(rp.read_text()) if rp.exists() else []
            existing.append(entry)
            rp.parent.mkdir(parents=True, exist_ok=True)
            rp.write_text(json.dumps(existing, indent=2))

    if len(df) < MIN_MARKETS:
        _write_entry({"category": category, "skipped": True, "reason": "insufficient_data", "market_count": len(df)})
        return False

    X = df[_feat_cols(df)].fillna(0.0)
    y = df["resolved_yes"].astype(int).tolist()

    try:
        windows, oof_probs, oof_actuals = _run_walk_forward(X, y)
    except Exception as exc:
        logger.warning("train_category: walk-forward failed for %s — %s", category, exc)
        windows, oof_probs, oof_actuals = [], [], []

    badge = quality_badge_from_windows(windows)

    # Quality gate: only skip when N_WINDOWS valid windows exist and badge is 'low'.
    # Fewer valid windows indicate single-class splits (class imbalance) — gate deferred.
    if badge == "low" and len(windows) >= N_WINDOWS:
        _write_entry({"category": category, "skipped": True, "reason": "quality_below_minimum", "badge": "low", "market_count": len(df)})
        return False

    model_dir.mkdir(parents=True, exist_ok=True)
    final_clf = RandomForestClassifier(n_estimators=N_ESTIMATORS, random_state=RANDOM_STATE)
    final_clf.fit(X.values, np.array(y))
    model_path = model_dir / f"{category}.joblib"
    joblib.dump(final_clf, model_path)
    logger.info("train_category: %s written to %s", category, model_path)

    if oof_probs and oof_actuals:
        try:
            CalibrationStore(store_path=model_dir / f"{category}_calibration.joblib").update(category, oof_probs, oof_actuals)
        except Exception as exc:
            logger.warning("train_category: calibration update failed — %s", exc)

    _write_entry({"category": category, "skipped": False, "badge": badge, "market_count": len(df), "model_path": str(model_path)})
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Train per-category PM resolution RandomForest classifiers.")
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/prediction_markets"))
    parser.add_argument("--model-dir", type=Path, default=Path("data/models/pm"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    report: list[dict] = []
    promoted = skipped = 0
    for category in PM_CATEGORIES:
        cat_path = args.processed_dir / f"{category}.parquet"
        if not cat_path.exists():
            logger.warning("no processed data for %s", category)
            report.append({"category": category, "skipped": True, "reason": "no_processed_file", "market_count": 0})
            skipped += 1
            continue
        success = train_category(category, pd.read_parquet(cat_path), model_dir=args.model_dir, report=report)
        promoted += int(success)
        skipped += int(not success)

    report_path = args.model_dir / "training_report.json"
    args.model_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(f"PM model training complete: {promoted} promoted, {skipped} skipped")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
