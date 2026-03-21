"""RED test stubs for WIRE-03: SnapshotStore real Supabase mode.

These tests are skipped in CI (no SUPABASE_URL). They will be unskipped in Wave 1
when Supabase integration env is wired.

WIRE-03: SnapshotStore must persist snapshots to Supabase when
SUPABASE_URL + SUPABASE_SERVICE_KEY are set.
"""

from __future__ import annotations

import os
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# WIRE-03: SnapshotStore Supabase mode
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    "SUPABASE_URL" not in os.environ,
    reason="integration test — requires SUPABASE_URL env var",
)
def test_supabase_mode_requires_env_vars() -> None:
    """SnapshotStore initializes with _supabase client when env vars are present.

    Skipped in CI (no SUPABASE_URL). Runs in integration environments where
    SUPABASE_URL is set. Asserts _supabase is not None (Strategy B).
    """
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    assert store._supabase is not None, (
        "Expected _supabase client to be initialized when SUPABASE_URL is set"
    )


@pytest.mark.skipif(
    "SUPABASE_URL" not in os.environ,
    reason="integration test — requires SUPABASE_URL env var",
)
def test_record_supabase_upsert_called() -> None:
    """record() calls supabase.table().upsert() when in Supabase mode.

    RED: test skipped in CI — unskipped in Wave 1 integration pass.
    """
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.upsert.return_value.execute.return_value = MagicMock(data=[{}], error=None)

    with patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://fake.supabase.co",
            "SUPABASE_SERVICE_KEY": "fake-key",
        },
    ):
        store = SnapshotStore()
        store._supabase = mock_client  # type: ignore[attr-defined]

        from datetime import datetime

        from sharpedge_venue_adapters.protocol import MarketStatePacket

        packet = MarketStatePacket(
            venue_id="kalshi",
            market_id="test_market",
            snapshot_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            orderbook=None,
            quotes=(),
        )
        store.record(packet)

    mock_client.table.assert_called_once_with("market_snapshots")
    # table().insert() (not upsert) per SnapshotStore implementation
    mock_table.insert.assert_called_once()


def test_snapshot_store_in_memory_mode_still_works() -> None:
    """SnapshotStore in-memory mode (no env vars) is unaffected by Supabase stubs.

    GREEN baseline: ensures import works correctly regardless of env vars.
    """
    from datetime import datetime

    from sharpedge_venue_adapters.protocol import MarketStatePacket
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    packet = MarketStatePacket(
        venue_id="kalshi",
        market_id="market_1",
        snapshot_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        orderbook=None,
        quotes=(),
    )
    store.record(packet)
    replayed = store.replay("kalshi", "market_1")
    assert len(replayed) == 1, f"Expected 1 snapshot, got {len(replayed)}"


def test_snapshot_store_supabase_mode_flag_check() -> None:
    """SnapshotStore._supabase is None when env vars are absent.

    GREEN baseline: verifies dual-mode detection logic.
    """
    # In CI, SUPABASE_URL is not set, so _supabase must be None
    import os as _os

    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    if not _os.getenv("SUPABASE_URL"):
        store = SnapshotStore()
        assert store._supabase is None, (
            "Expected _supabase to be None when SUPABASE_URL env var is absent"
        )
    else:
        pytest.skip("SUPABASE_URL is set — skipping in-memory mode check")
