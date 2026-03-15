"""RED TDD stubs for full model pipeline integration — PIPE-01.

Tests lock the interface contracts for:
  - train_ensemble: data -> EnsembleManager
  - WalkForwardBacktester: run_with_model_inference -> BacktestReport with quality_badge
  - CalibrationStore: update + get_confidence_mult
  - Full pipeline chain: data -> train -> backtest -> calibrate -> alpha

These tests must remain FAILING (RED) until Wave 1–5 implementation.
Do NOT add pytest.skip() calls.
"""
from __future__ import annotations


def test_ensemble_trains_all_sports():
    """train_ensemble must be called with a DataFrame covering all 5 sports.

    RED: raises NotImplementedError until Wave 1 trains per-sport models.
    """
    import numpy as np
    import pandas as pd
    from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES, train_ensemble

    rng = np.random.default_rng(42)
    n = 200
    sports = ["nba", "nfl", "mlb", "nhl", "ncaab"]
    records = []
    for i in range(n):
        sport = sports[i % len(sports)]
        row = {"sport": sport}
        for domain, cols in DOMAIN_FEATURES.items():
            for col in cols:
                row[col] = rng.random()
        records.append(row)
    df = pd.DataFrame(records)

    y = rng.integers(0, 2, size=n).astype(float)

    sports_in_df = set(df["sport"].unique())
    expected_sports = {"nba", "nfl", "mlb", "nhl", "ncaab"}
    assert expected_sports.issubset(sports_in_df), (
        f"DataFrame must contain all 5 sports; missing: {expected_sports - sports_in_df}"
    )

    raise NotImplementedError(
        "PIPE-01: train_ensemble multi-sport training not yet implemented. "
        "Wave 1 must call train_ensemble per sport and persist per-sport EnsembleManager."
    )


def test_walk_forward_produces_quality_badge():
    """WalkForwardBacktester.run_with_model_inference must return BacktestReport with
    quality_badge in ['high', 'excellent'].

    RED: raises NotImplementedError until Wave 2 implements walk-forward with badge.
    """
    import numpy as np
    import pandas as pd
    from sharpedge_models.walk_forward import BacktestReport, WalkForwardBacktester

    rng = np.random.default_rng(1)
    n = 300
    feature_df = pd.DataFrame(rng.random((n, 10)), columns=[f"feat_{i}" for i in range(10)])
    y = rng.integers(0, 2, size=n).astype(float)

    def dummy_model_fn(X: pd.DataFrame) -> np.ndarray:
        return np.full(len(X), 0.55)

    backtester = WalkForwardBacktester()

    raise NotImplementedError(
        "PIPE-01: WalkForwardBacktester.run_with_model_inference not yet wired to "
        "per-sport model inference. Wave 2 must return BacktestReport with "
        "quality_badge in ['high', 'excellent']."
    )

    # Assertions that must pass post-implementation:
    # report = backtester.run_with_model_inference(feature_df, dummy_model_fn, y, n_windows=4)
    # assert isinstance(report, BacktestReport)
    # assert report.quality_badge in ("high", "excellent"), (
    #     f"Expected high/excellent badge, got: {report.quality_badge}"
    # )


def test_calibration_store_updates_confidence_mult():
    """CalibrationStore.get_confidence_mult must return < 1.0 after update with >=50 games.

    RED: raises NotImplementedError until Wave 3 implements per-sport calibration update.
    """
    import numpy as np
    from sharpedge_models.calibration_store import BRIER_GOOD, MIN_GAMES, CalibrationStore

    rng = np.random.default_rng(2)
    n = MIN_GAMES + 10

    # Well-calibrated predictions (probs near outcomes)
    outcomes = rng.integers(0, 2, size=n).tolist()
    probs = [float(o) * 0.9 + 0.05 for o in outcomes]

    store = CalibrationStore()

    raise NotImplementedError(
        "PIPE-01: CalibrationStore.update + get_confidence_mult multi-sport path not yet "
        "implemented. Wave 3 must update per-sport Platt calibration and return "
        "confidence_mult < 1.0 when brier score is below BRIER_GOOD threshold."
    )

    # Assertions that must pass post-implementation:
    # store.update("nba", probs, [bool(o) for o in outcomes])
    # mult = store.get_confidence_mult("nba")
    # assert mult < 1.0, f"Expected confidence_mult < 1.0 for well-calibrated model, got {mult}"
    # assert 0.5 <= mult <= 1.2, f"confidence_mult must be clamped to [0.5, 1.2], got {mult}"


def test_pipeline_end_to_end():
    """Full chain: data -> train_ensemble -> walk_forward -> calibrate -> compose_alpha
    must produce alpha > 0.0.

    RED: raises NotImplementedError until all waves are complete and wired together.
    """
    raise NotImplementedError(
        "PIPE-01: End-to-end pipeline not yet implemented. "
        "Requires Wave 1 (train), Wave 2 (backtest), Wave 3 (calibrate), "
        "Wave 4 (alpha) to be complete and integrated."
    )

    # Assertions that must pass post-implementation:
    # import numpy as np
    # import pandas as pd
    # from pathlib import Path
    # from sharpedge_models.ensemble_trainer import DOMAIN_FEATURES, train_ensemble
    # from sharpedge_models.walk_forward import WalkForwardBacktester
    # df = ... (multi-sport DataFrame)
    # y = np.random.default_rng(3).integers(0, 2, size=len(df)).astype(float)
    # em = train_ensemble(df, y, Path("/tmp/test_models"), "test_v1")
    # backtester = WalkForwardBacktester()
    # report = backtester.run_with_model_inference(df, em.predict, y)
    # assert report.quality_badge in ("high", "excellent")
    # alpha_result = {"alpha": 0.5}  # placeholder
    # assert alpha_result["alpha"] > 0.0
