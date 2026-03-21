"""LedgerStore (SettlementLedger) Supabase mode verification.

Required environment variables (SKIPPED in CI unless SUPABASE_URL is set):
  SUPABASE_URL               — Supabase project URL
  SUPABASE_SERVICE_KEY  — service-role key (bypasses RLS)

WIRE-03: 2 tests — SKIPPED in CI; ready to run against real Supabase instance.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sharpedge_venue_adapters.ledger import LedgerEntry, SettlementLedger

# ---------------------------------------------------------------------------
# Module-level skip guard — entire file skipped when SUPABASE_URL is absent
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"),
    reason="integration test — requires SUPABASE_URL",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry() -> LedgerEntry:
    """Build a minimal valid LedgerEntry for testing."""
    now = datetime.now(UTC)
    return LedgerEntry(
        entry_id=None,
        event_type="FILL",
        venue_id="kalshi",
        market_id="KXTEST-26",
        position_lot_id="LOT-SUPABASE-TEST",
        amount_usdc=-50.0,
        fee_component=0.0,
        rebate_component=0.0,
        price_at_event=0.55,
        occurred_at=now,
        recorded_at=now,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ledger_store_supabase_mode_not_none() -> None:
    """SettlementLedger._supabase is not None when env vars are present.

    Mirrors the pattern in test_snapshot_store.py Supabase mode tests.
    """
    store = SettlementLedger()
    assert store._supabase is not None, (
        "Expected Supabase client to be initialised when SUPABASE_URL and "
        "SUPABASE_SERVICE_KEY are present"
    )


def test_ledger_store_record_calls_insert() -> None:
    """SettlementLedger.append() calls table('ledger_entries').insert() in Supabase mode.

    Mocks the Supabase insert chain to verify the write path without hitting a real DB.
    """
    store = SettlementLedger()

    # Build a mock insert chain: .table(...).insert(...).execute()
    mock_execute = MagicMock(return_value=MagicMock(data=[{"entry_id": 42}]))
    mock_insert = MagicMock(return_value=MagicMock(execute=mock_execute))
    mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))
    store._supabase = MagicMock(table=mock_table)

    entry = _make_entry()
    stored = store.append(entry)

    mock_table.assert_called_once_with("ledger_entries")
    mock_insert.assert_called_once()
    mock_execute.assert_called_once()
    assert stored.entry_id == 42
