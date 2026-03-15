#!/usr/bin/env python3
"""Walk-forward backtesting orchestrator for SharpEdge.

Loads data/processed/{sport}_training.parquet, runs WalkForwardBacktester
.run_with_model_inference() with GBM+StandardScaler, and saves:
    data/walk_forward_{sport}_report.json

Usage:
    uv run python scripts/run_walk_forward.py --sport nba [--n-windows 4] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# Columns excluded from feature selection (mirrors train_models.get_feature_columns)
_EXCLUDE_COLUMNS = {
    "game_date", "season", "home_team", "away_team",
    "home_score", "away_score", "total_points", "point_diff",
    "spread_result", "total_result", "home_covered", "went_over",
    "spread_line", "total_line",
}


# ---------------------------------------------------------------------------
# Helpers — only stdlib + numpy needed here so importlib can load this file
# without pandas/sklearn in the test venv
# ---------------------------------------------------------------------------

def compute_max_drawdown(window_rois: list[float]) -> float:
    """Max drawdown from per-window ROI sequence. Returns 0.0 if all positive."""
    import numpy as np  # deferred so tests can import without full scipy stack
    if not window_rois:
        return 0.0
    wealth = np.cumprod([1.0 + r for r in window_rois])
    peak = np.maximum.accumulate(wealth)
    drawdowns = (peak - wealth) / peak
    return float(drawdowns.max())


def _get_feature_columns(df) -> list[str]:  # type: ignore[no-untyped-def]
    """Return numeric columns excluding metadata."""
    import numpy as np
    return [
        col for col in df.columns
        if col not in _EXCLUDE_COLUMNS
        and df[col].dtype in (np.float64, np.int64, np.bool_)
    ]


def _build_model_fn():
    """Return a GBM+StandardScaler model_fn for run_with_model_inference."""
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    def model_fn(X_train, X_test, y_train):  # type: ignore[no-untyped-def]
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=100, random_state=42)),
        ])
        pipe.fit(X_train, y_train)
        return pipe

    return model_fn


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def run_walk_forward(sport: str, n_windows: int = 4) -> dict:
    """Load parquet for *sport*, run walk-forward, save and return JSON report dict."""
    import pandas as pd
    from sharpedge_models.walk_forward import WalkForwardBacktester

    parquet_path = PROCESSED_DIR / f"{sport}_training.parquet"
    if not parquet_path.exists():
        print(f"ERROR: Processed parquet not found: {parquet_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df)} rows from {parquet_path}")

    if "home_covered" not in df.columns:
        print(f"ERROR: 'home_covered' column missing in {parquet_path}", file=sys.stderr)
        sys.exit(1)

    feature_cols = _get_feature_columns(df)
    if not feature_cols:
        print("ERROR: No numeric feature columns found.", file=sys.stderr)
        sys.exit(1)

    valid_mask = df["home_covered"].notna()
    for col in feature_cols:
        valid_mask &= df[col].notna()

    df_valid = df[valid_mask].copy()
    print(f"Valid rows after filtering: {len(df_valid)} | features: {len(feature_cols)}")

    feature_df = df_valid[feature_cols].reset_index(drop=True)
    y = df_valid["home_covered"].astype(int).values

    backtester = WalkForwardBacktester()
    report = backtester.run_with_model_inference(
        feature_df, _build_model_fn(), y, n_windows=n_windows
    )

    window_rois = [w.out_of_sample_roi for w in report.windows]
    max_dd = compute_max_drawdown(window_rois)

    windows_list = [
        {"window_id": w.window_id, "roi": w.out_of_sample_roi,
         "win_rate": w.out_of_sample_win_rate, "n_bets": w.n_bets}
        for w in report.windows
    ]

    report_dict = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sport": sport,
        "quality_badge": report.quality_badge,
        "overall_roi": report.overall_roi,
        "overall_win_rate": report.overall_win_rate,
        "max_drawdown": max_dd,
        "n_windows": len(report.windows),
        "windows": windows_list,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"walk_forward_{sport}_report.json"
    with open(report_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    print(f"Report saved to {report_path}")
    print(f"quality_badge: {report.quality_badge}")
    return report_dict


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Walk-forward backtesting orchestrator for SharpEdge."
    )
    parser.add_argument("--sport", default="nba", help="Sport to backtest (default: nba)")
    parser.add_argument("--n-windows", type=int, default=4, dest="n_windows",
                        help="Number of walk-forward windows (default: 4)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print feature/row counts without running backtester")
    args = parser.parse_args()

    if args.dry_run:
        import pandas as pd
        parquet_path = PROCESSED_DIR / f"{args.sport}_training.parquet"
        if not parquet_path.exists():
            print(f"ERROR: Processed parquet not found: {parquet_path}", file=sys.stderr)
            sys.exit(1)
        df = pd.read_parquet(parquet_path)
        feature_cols = _get_feature_columns(df)
        print(f"rows={len(df)} features={len(feature_cols)}")
        return

    run_walk_forward(args.sport, n_windows=args.n_windows)


if __name__ == "__main__":
    main()
