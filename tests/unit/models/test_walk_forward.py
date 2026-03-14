"""Failing test stubs for QUANT-05: Walk-forward backtesting windows."""


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
