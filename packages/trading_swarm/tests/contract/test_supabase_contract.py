"""Contract tests for Supabase — verifies schema matches code expectations."""

import os
from datetime import UTC, datetime

import pytest


@pytest.fixture(scope="module")
def supabase_client(require_supabase):
    from supabase import create_client

    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"],
    )


def test_paper_trades_table_accepts_insert(supabase_client):
    """paper_trades table exists and accepts a row with the expected schema."""
    test_id = "contract-test-" + datetime.now(tz=UTC).strftime("%Y%m%d%H%M%S%f")
    row = {
        "market_id": test_id,
        "direction": "yes",
        "size": 10.0,
        "entry_price": 0.45,
        "confidence_score": 0.72,
        "category": "economic",
        "trading_mode": "paper",
        "opened_at": datetime.now(tz=UTC).isoformat(),
    }
    try:
        resp = supabase_client.table("paper_trades").insert(row).execute()
        assert resp.data, "Insert should return inserted row data"
        inserted_id = resp.data[0].get("id")
        assert inserted_id, "Inserted row should have an id"
    finally:
        # Always clean up the test row
        supabase_client.table("paper_trades").delete().eq("market_id", test_id).execute()


def test_open_positions_table_readable(supabase_client):
    """open_positions table exists and is queryable."""
    resp = supabase_client.table("open_positions").select("id,market_id,status").limit(1).execute()
    # Just assert no exception and response has .data attribute (list, possibly empty)
    assert isinstance(resp.data, list), "open_positions.select should return a list"


def test_trading_config_table_has_default_keys(supabase_client):
    """trading_config table has the default config keys."""
    resp = supabase_client.table("trading_config").select("key,value").execute()
    keys = {row["key"] for row in resp.data}
    expected_keys = {
        "confidence_threshold",
        "kelly_fraction",
        "max_category_exposure",
        "max_total_exposure",
        "daily_loss_limit",
    }
    missing = expected_keys - keys
    assert not missing, f"trading_config missing expected keys: {missing}"


def test_trade_post_mortems_table_accepts_insert(supabase_client):
    """trade_post_mortems table exists and accepts a row."""
    row = {
        "trade_id": "00000000-0000-0000-0000-000000000001",  # fake uuid
        "model_error_score": 0.0,
        "signal_error_score": 0.0,
        "sizing_error_score": 0.0,
        "variance_score": 1.0,
        "llm_narrative": "Contract test row — safe to delete",
    }
    try:
        resp = supabase_client.table("trade_post_mortems").insert(row).execute()
        assert resp.data, "Insert should return data"
        resp.data[0].get("id")
    finally:
        supabase_client.table("trade_post_mortems").delete().eq(
            "llm_narrative", "Contract test row — safe to delete"
        ).execute()
