"""Contract stub tests for process_pm_historical script — Phase 9 plan 01.

The script does not exist yet (implemented in plan 04).
Tests use pytest.mark.xfail to document the interface contract without
requiring the script to exist. All assertions are RED / xfail stubs.
"""

import pytest


UNIVERSAL_FEATURE_COLS = [
    "market_prob",
    "bid_ask_spread",
    "last_price",
    "volume",
    "open_interest",
    "days_to_close",
]


# ---------------------------------------------------------------------------
# xfail RED stubs — document the process_pm_historical contract
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="plan 04 implementation pending — script not yet created")
def test_process_kalshi_adds_universal_features(tmp_path):
    """Given raw Kalshi parquet → output DataFrame has all 6 universal feature columns."""
    import pandas as pd

    from scripts.process_pm_historical import process_kalshi  # noqa: F401

    # Create minimal raw parquet fixture.
    raw_df = pd.DataFrame({
        "ticker": ["KXBTC-100K"],
        "result": ["yes"],
        "volume": [5000.0],
        "open_interest": [200.0],
        "last_price": [0.6],
        "yes_bid": [0.58],
        "yes_ask": [0.62],
        "close_time": ["2024-12-01T00:00:00Z"],
        "event_ticker": ["KXBTC"],
    })
    raw_path = tmp_path / "kalshi_raw.parquet"
    raw_df.to_parquet(raw_path)

    output_df = process_kalshi(raw_path)

    assert isinstance(output_df, pd.DataFrame)
    for col in UNIVERSAL_FEATURE_COLS:
        assert col in output_df.columns, f"Missing universal feature column: {col}"


@pytest.mark.xfail(reason="plan 04 implementation pending — script not yet created")
def test_process_polymarket_adds_universal_features(tmp_path):
    """Given raw Polymarket parquet → output DataFrame has all 6 universal feature columns."""
    import pandas as pd

    from scripts.process_pm_historical import process_polymarket  # noqa: F401

    raw_df = pd.DataFrame({
        "condition_id": ["0xabc123"],
        "question": ["Will BTC reach $100k?"],
        "volume": [10000.0],
        "liquidity": [500.0],
        "end_date": ["2024-12-31"],
        "category": ["crypto"],
        "resolved_yes": [True],
    })
    raw_path = tmp_path / "poly_raw.parquet"
    raw_df.to_parquet(raw_path)

    output_df = process_polymarket(raw_path)

    assert isinstance(output_df, pd.DataFrame)
    for col in UNIVERSAL_FEATURE_COLS:
        assert col in output_df.columns, f"Missing universal feature column: {col}"


@pytest.mark.xfail(reason="plan 04 implementation pending — script not yet created")
def test_low_data_category_filtered_count(tmp_path):
    """Category with < 200 markets → JSON report entry has 'skipped': true."""
    import json
    import pandas as pd

    from scripts.process_pm_historical import process_and_report  # noqa: F401

    # 50 rows of crypto — below the 200-market threshold.
    raw_df = pd.DataFrame({
        "category": ["crypto"] * 50,
        "market_prob": [0.5] * 50,
        "volume": [1000.0] * 50,
    })
    raw_path = tmp_path / "small_crypto.parquet"
    raw_df.to_parquet(raw_path)

    report_path = tmp_path / "report.json"
    process_and_report(raw_path, report_path)

    with open(report_path) as f:
        report = json.load(f)

    crypto_entry = next((e for e in report if e.get("category") == "crypto"), None)
    assert crypto_entry is not None
    assert crypto_entry["skipped"] is True
