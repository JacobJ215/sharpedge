"""Walk-forward backtesting windows for out-of-sample model validation.

Walk-forward analysis partitions historical data into non-overlapping
expanding-train / fixed-test windows. Each window trains on all data
before its test period, ensuring no data leakage.

CRITICAL INVARIANT: set(train_ids) & set(test_ids) == set() for every window.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

__all__ = [
    "BacktestReport",
    "WalkForwardBacktester",
    "WindowResult",
    "create_windows",
    "quality_badge_from_windows",
]


@dataclass
class WindowResult:
    """Result of a single walk-forward window."""

    window_id: int
    train_ids: list  # IDs of training-set records
    test_ids: list  # IDs of test-set records
    out_of_sample_win_rate: float
    out_of_sample_roi: float
    n_bets: int


@dataclass
class BacktestReport:
    """Aggregate report across all walk-forward windows."""

    windows: list[WindowResult]
    overall_win_rate: float
    overall_roi: float
    quality_badge: Literal["low", "medium", "high", "excellent"]


def create_windows(
    all_ids: list,
    n_windows: int = 4,
) -> list[WindowResult]:
    """Partition IDs into non-overlapping expanding-train / fixed-test windows.

    Window design: the IDs list is split into (n_windows + 1) roughly equal
    chunks. Each test window is chunk[i+1]; the corresponding train set is all
    chunks up to and including chunk[i] (expanding window).

    CRITICAL: assert set(train_ids) & set(test_ids) == set() for every window.

    Args:
        all_ids: Ordered sequence of record identifiers
        n_windows: Number of walk-forward windows to produce

    Returns:
        List of WindowResult, one per window, with zero train/test overlap.
    """
    ids = list(all_ids)
    total = len(ids)

    if n_windows < 1:
        raise ValueError("n_windows must be >= 1")

    # Divide into n_windows + 1 chunks so we have n_windows train/test splits.
    n_chunks = n_windows + 1
    chunk_size = total // n_chunks
    remainder = total % n_chunks

    # Build chunk boundaries
    chunks: list[list] = []
    start = 0
    for i in range(n_chunks):
        # Distribute remainder across first `remainder` chunks
        size = chunk_size + (1 if i < remainder else 0)
        chunks.append(ids[start : start + size])
        start += size

    windows: list[WindowResult] = []
    for i in range(n_windows):
        # Train: all chunks up to and including chunk[i]
        train_ids: list = []
        for j in range(i + 1):
            train_ids.extend(chunks[j])

        # Test: chunk[i+1]
        test_ids: list = list(chunks[i + 1])

        # CRITICAL INVARIANT: zero overlap
        assert not (set(str(t) for t in train_ids) & set(str(t) for t in test_ids)), (
            f"Window {i} has train/test overlap"
        )

        windows.append(
            WindowResult(
                window_id=i,
                train_ids=train_ids,
                test_ids=test_ids,
                out_of_sample_win_rate=0.0,
                out_of_sample_roi=0.0,
                n_bets=len(test_ids),
            )
        )

    return windows


def quality_badge_from_windows(
    windows: list[WindowResult],
) -> Literal["low", "medium", "high", "excellent"]:
    """Assign quality badge based on window count and positive-ROI windows.

    Thresholds:
      - "low"       : fewer than 2 windows
      - "excellent" : 4+ windows with 3+ positive ROI
      - "high"      : 3+ windows with 2+ positive ROI
      - "medium"    : 2+ windows with 1+ positive ROI
      - "low"       : fallback (2+ windows but none positive)

    Args:
        windows: List of WindowResult from create_windows()

    Returns:
        Quality badge string
    """
    if len(windows) < 2:
        return "low"

    n_positive = sum(1 for w in windows if w.out_of_sample_roi > 0)

    if len(windows) >= 4 and n_positive >= 3:
        return "excellent"
    elif len(windows) >= 3 and n_positive >= 2:
        return "high"
    elif n_positive >= 1:
        return "medium"

    return "low"


class WalkForwardBacktester:
    """Run walk-forward backtest over stored BacktestResults from BacktestEngine."""

    def run(
        self,
        results: list,  # list[BacktestResult] from BacktestEngine._fetch_resolved_predictions
        n_windows: int = 4,
    ) -> BacktestReport:
        """Partition resolved results into windows and compute per-window metrics.

        Sorts by timestamp before partitioning (chronological order required
        for valid out-of-sample testing).

        Args:
            results: List of BacktestResult objects with outcome, odds, timestamp
            n_windows: Number of walk-forward windows

        Returns:
            BacktestReport with per-window metrics and overall quality badge
        """
        if not results:
            return BacktestReport(
                windows=[],
                overall_win_rate=0.0,
                overall_roi=0.0,
                quality_badge="low",
            )

        # Sort chronologically
        sorted_results = sorted(results, key=lambda r: r.timestamp)
        all_ids = [r.prediction_id for r in sorted_results]

        windows = create_windows(all_ids, n_windows=n_windows)

        # Build lookup for results by prediction_id
        result_by_id = {r.prediction_id: r for r in sorted_results}

        computed_windows: list[WindowResult] = []
        for w in windows:
            test_results = [result_by_id[pid] for pid in w.test_ids if pid in result_by_id]
            resolved = [r for r in test_results if r.outcome is not None]

            if not resolved:
                computed_windows.append(
                    WindowResult(
                        window_id=w.window_id,
                        train_ids=w.train_ids,
                        test_ids=w.test_ids,
                        out_of_sample_win_rate=0.0,
                        out_of_sample_roi=0.0,
                        n_bets=0,
                    )
                )
                continue

            wins = sum(1 for r in resolved if r.outcome)
            win_rate = wins / len(resolved)

            # ROI: sum of returns per bet. Win returns (decimal_odds - 1), loss returns -1.
            total_return = 0.0
            for r in resolved:
                if r.outcome:
                    if r.odds > 0:
                        total_return += r.odds / 100
                    else:
                        total_return += 100 / abs(r.odds)
                else:
                    total_return -= 1.0
            roi = total_return / len(resolved)

            computed_windows.append(
                WindowResult(
                    window_id=w.window_id,
                    train_ids=w.train_ids,
                    test_ids=w.test_ids,
                    out_of_sample_win_rate=win_rate,
                    out_of_sample_roi=roi,
                    n_bets=len(resolved),
                )
            )

        # Weighted averages by n_bets
        total_bets = sum(w.n_bets for w in computed_windows)
        if total_bets > 0:
            overall_win_rate = (
                sum(w.out_of_sample_win_rate * w.n_bets for w in computed_windows) / total_bets
            )
            overall_roi = sum(w.out_of_sample_roi * w.n_bets for w in computed_windows) / total_bets
        else:
            overall_win_rate = 0.0
            overall_roi = 0.0

        badge = quality_badge_from_windows(computed_windows)

        return BacktestReport(
            windows=computed_windows,
            overall_win_rate=overall_win_rate,
            overall_roi=overall_roi,
            quality_badge=badge,
        )

    def run_with_model_inference(
        self,
        feature_df: pd.DataFrame,
        model_fn: Callable,
        y: np.ndarray,
        n_windows: int = 4,
    ) -> BacktestReport:
        """Run honest walk-forward validation using actual model inference per window.

        This method drives training + inference per window — NOT reading stored IDs.
        Produces quality badges based on true out-of-sample predictions.

        Args:
            feature_df: Full feature DataFrame (rows = games, chronological order).
            model_fn: Callable(X_train, X_test, y_train) -> predictor with predict_proba().
            y: Binary outcome array (same length as feature_df).
            n_windows: Number of walk-forward windows.

        Returns:
            BacktestReport with honest out-of-sample metrics.
        """
        n = len(feature_df)
        chunk_size = n // (n_windows + 1)
        windows: list[WindowResult] = []

        for w in range(n_windows):
            train_end = (w + 1) * chunk_size
            test_start = train_end
            test_end = min(test_start + chunk_size, n)

            X_train = feature_df.iloc[:train_end]
            X_test = feature_df.iloc[test_start:test_end]
            y_train = y[:train_end]
            y_test = y[test_start:test_end]

            if len(X_test) == 0 or len(np.unique(y_train)) < 2:
                continue

            try:
                predictor = model_fn(X_train, X_test, y_train)
                probs = predictor.predict_proba(X_test)[:, 1]
                preds = (probs >= 0.5).astype(int)
                win_rate = float(np.mean(preds == y_test))
                wins = int(np.sum(preds == y_test))
                losses = len(y_test) - wins
                roi = (wins * (100 / 110) - losses) / len(y_test)
            except Exception:
                win_rate = 0.5
                roi = 0.0

            windows.append(
                WindowResult(
                    window_id=w,
                    train_ids=list(range(train_end)),
                    test_ids=list(range(test_start, test_end)),
                    out_of_sample_win_rate=win_rate,
                    out_of_sample_roi=roi,
                    n_bets=len(X_test),
                )
            )

        return BacktestReport(
            windows=windows,
            overall_win_rate=float(np.mean([w.out_of_sample_win_rate for w in windows]))
            if windows
            else 0.5,
            overall_roi=float(np.mean([w.out_of_sample_roi for w in windows])) if windows else 0.0,
            quality_badge=quality_badge_from_windows(windows),
        )
