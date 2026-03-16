"""Tests for train_pm_models script.

Phase 9 plan 04/05 implemented the script. Tests no longer xfail.
Phase 10 plan 01 adds Wave 0 coverage for the calibration_score key.
"""

import pytest


# ---------------------------------------------------------------------------
# GREEN tests — train_pm_models contract (xfail removed, script exists)
# ---------------------------------------------------------------------------

def test_train_skips_category_below_200(tmp_path):
    """Category with 150 rows → no model artifact, JSON report entry has 'skipped': true."""
    import json
    import pandas as pd

    from scripts.train_pm_models import train_category  # noqa: F401

    # 150 rows for "crypto" category — below 200-market threshold.
    df = pd.DataFrame({
        "category": ["crypto"] * 150,
        "market_prob": [0.5] * 150,
        "volume": [1000.0] * 150,
        "resolved_yes": ([True] * 75) + ([False] * 75),
    })

    model_dir = tmp_path / "models"
    report_path = tmp_path / "report.json"

    train_category("crypto", df, model_dir=model_dir, report_path=report_path)

    # No model artifact should be written.
    artifact = model_dir / "crypto.joblib"
    assert not artifact.exists(), "Model artifact should NOT be written for < 200 samples"

    with open(report_path) as f:
        report = json.load(f)

    crypto_entry = next((e for e in report if e.get("category") == "crypto"), None)
    assert crypto_entry is not None
    assert crypto_entry["skipped"] is True


def test_train_produces_joblib_artifact(tmp_path):
    """Category with 300 rows (mocked) → data/models/pm/{category}.joblib written."""
    import pandas as pd

    from scripts.train_pm_models import train_category  # noqa: F401

    # 300 rows — above 200-market threshold.
    df = pd.DataFrame({
        "category": ["political"] * 300,
        "market_prob": [0.5] * 300,
        "volume": [1000.0] * 300,
        "bid_ask_spread": [0.04] * 300,
        "last_price": [0.5] * 300,
        "open_interest": [200.0] * 300,
        "days_to_close": [7] * 300,
        "resolved_yes": ([True] * 150) + ([False] * 150),
    })

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True)
    report_path = tmp_path / "report.json"

    train_category("political", df, model_dir=model_dir, report_path=report_path)

    artifact = model_dir / "political.joblib"
    assert artifact.exists(), "Model artifact should be written for >= 200 samples"


def test_walk_forward_requires_3_windows(tmp_path):
    """Category with < 150 markets (3 × 50) → quality_badge returns 'low', category skipped."""
    import pandas as pd

    from scripts.train_pm_models import train_category  # noqa: F401

    # 120 rows — can form at most 2 complete windows of 50 with holdout.
    df = pd.DataFrame({
        "category": ["weather"] * 120,
        "market_prob": [0.5] * 120,
        "volume": [1000.0] * 120,
        "resolved_yes": ([True] * 60) + ([False] * 60),
    })

    model_dir = tmp_path / "models"
    report_path = tmp_path / "report.json"

    train_category("weather", df, model_dir=model_dir, report_path=report_path)

    artifact = model_dir / "weather.joblib"
    assert not artifact.exists(), "Category skipped when < 3 walk-forward windows possible"


# ---------------------------------------------------------------------------
# Wave 0 test — RED until Plan 03 adds calibration_score key to report entry
# ---------------------------------------------------------------------------

def test_train_category_report_includes_calibration_score(tmp_path):
    """Successful train_category() → report JSON entry has a 'calibration_score' key.

    Value may be None if OOF fails (e.g. insufficient windows), but the key
    must always be present so downstream tooling can rely on the schema.

    RED until Plan 03 adds calibration_score to the report entry written by
    train_category().
    """
    import json
    import pandas as pd

    from scripts.train_pm_models import train_category

    # 300 balanced rows — enough to pass the MIN_MARKETS gate and train a model.
    df = pd.DataFrame({
        "category": ["political"] * 300,
        "market_prob": [0.5] * 300,
        "volume": [1000.0] * 300,
        "bid_ask_spread": [0.04] * 300,
        "last_price": [0.5] * 300,
        "open_interest": [200.0] * 300,
        "days_to_close": [7] * 300,
        "resolved_yes": ([1] * 150) + ([0] * 150),
    })

    model_dir = tmp_path / "models"
    model_dir.mkdir(parents=True)
    report_path = tmp_path / "report.json"

    train_category("political", df, model_dir=model_dir, report_path=report_path)

    with open(report_path) as f:
        report = json.load(f)

    political_entry = next((e for e in report if e.get("category") == "political"), None)
    assert political_entry is not None, "Report must contain an entry for 'political'"
    assert "calibration_score" in political_entry, (
        "Report entry must contain 'calibration_score' key (value may be None)"
    )
