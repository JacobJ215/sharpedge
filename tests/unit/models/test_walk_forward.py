"""Tests for walk_forward module: QUANT-05 and MODEL-01 run_with_model_inference."""
import pytest


def test_no_overlap():
    """Walk-forward windows have zero train/test ID overlap."""
    from sharpedge_models.walk_forward import create_windows
    windows = create_windows(
        all_ids=list(range(100)),
        n_windows=4,
    )
    for w in windows:
        overlap = set(w.train_ids) & set(w.test_ids)
        assert len(overlap) == 0, f"Window {w.window_id} has {len(overlap)} overlapping IDs"


def test_quality_badge_low():
    """quality_badge='low' when fewer than 2 windows."""
    from sharpedge_models.walk_forward import WindowResult, quality_badge_from_windows
    windows = [WindowResult(window_id=0, train_ids=[], test_ids=[], out_of_sample_win_rate=0.5,
                            out_of_sample_roi=0.05, n_bets=10)]
    assert quality_badge_from_windows(windows) == "low"


def test_quality_badge_excellent():
    """quality_badge='excellent' for >= 4 windows with 3+ positive ROI."""
    from sharpedge_models.walk_forward import WindowResult, quality_badge_from_windows
    windows = [
        WindowResult(window_id=i, train_ids=[], test_ids=[],
                     out_of_sample_win_rate=0.53, out_of_sample_roi=0.04, n_bets=20)
        for i in range(4)
    ]
    assert quality_badge_from_windows(windows) == "excellent"


def test_run_with_inference_produces_report():
    """run_with_model_inference with LogisticRegression produces a valid BacktestReport."""
    pd = pytest.importorskip("pandas")
    sklearn_linear = pytest.importorskip("sklearn.linear_model")
    import numpy as np
    LogisticRegression = sklearn_linear.LogisticRegression

    from sharpedge_models.walk_forward import WalkForwardBacktester

    rng = np.random.default_rng(42)
    n = 100
    feature_df = pd.DataFrame({"x1": rng.standard_normal(n), "x2": rng.standard_normal(n)})
    y = (rng.random(n) > 0.5).astype(int)

    def model_fn(X_train, X_test, y_train):
        clf = LogisticRegression(max_iter=200)
        clf.fit(X_train, y_train)
        return clf

    backtester = WalkForwardBacktester()
    report = backtester.run_with_model_inference(feature_df, model_fn, y, n_windows=4)

    assert report.quality_badge in {"low", "medium", "high", "excellent"}, (
        f"Unexpected quality_badge: {report.quality_badge}"
    )
    assert 0.0 <= report.overall_win_rate <= 1.0
    assert len(report.windows) > 0


def test_run_with_inference_no_lookahead():
    """Train split rows all have lower indices than test split rows in every window."""
    pd = pytest.importorskip("pandas")
    sklearn_linear = pytest.importorskip("sklearn.linear_model")
    import numpy as np
    LogisticRegression = sklearn_linear.LogisticRegression

    from sharpedge_models.walk_forward import WalkForwardBacktester

    rng = np.random.default_rng(7)
    n = 80
    feature_df = pd.DataFrame({"x1": rng.standard_normal(n)})
    y = (rng.random(n) > 0.5).astype(int)

    def model_fn(X_train, X_test, y_train):
        clf = LogisticRegression(max_iter=200)
        clf.fit(X_train, y_train)
        return clf

    backtester = WalkForwardBacktester()
    report = backtester.run_with_model_inference(feature_df, model_fn, y, n_windows=3)

    for window in report.windows:
        max_train = max(window.train_ids) if window.train_ids else -1
        min_test = min(window.test_ids) if window.test_ids else float("inf")
        assert max_train < min_test, (
            f"Window {window.window_id}: train max {max_train} >= test min {min_test} (lookahead!)"
        )
