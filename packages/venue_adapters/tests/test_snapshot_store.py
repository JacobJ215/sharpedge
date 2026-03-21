"""Tests for SnapshotStore: append-only market state snapshot persistence.

Covers the locked CONTEXT.md principle:
  "Deterministic replay: every market-state snapshot must be replayable from stored events"
"""

from datetime import UTC, datetime

import pytest


def _make_packet(venue_id: str, market_id: str, snapshot_at_utc: datetime):
    from sharpedge_venue_adapters.protocol import (
        CanonicalOrderBook,
        MarketStatePacket,
    )

    return MarketStatePacket(
        venue_id=venue_id,
        market_id=market_id,
        snapshot_at=snapshot_at_utc.isoformat(),
        orderbook=CanonicalOrderBook(
            bids=({"price": 0.48, "size": 100},),
            asks=({"price": 0.52, "size": 100},),
            timestamp_utc=snapshot_at_utc.isoformat(),
        ),
        quotes=(),
    )


def test_record_and_replay():
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    packet = _make_packet(
        "kalshi", "KXBTCD-01", datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC)
    )
    store.record(packet)
    replayed = store.replay("kalshi", "KXBTCD-01")
    assert len(replayed) == 1
    assert replayed[0].market_id == "KXBTCD-01"


def test_replay_sorted_by_snapshot_at():
    """Packets recorded out of order must come back sorted ascending by snapshot_at."""
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    t1 = datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 3, 14, 12, 5, 0, tzinfo=UTC)
    # Record later timestamp first
    store.record(_make_packet("kalshi", "KXBTCD-01", t2))
    store.record(_make_packet("kalshi", "KXBTCD-01", t1))
    replayed = store.replay("kalshi", "KXBTCD-01")
    assert replayed[0].snapshot_at < replayed[1].snapshot_at


def test_replay_is_deterministic():
    """Two calls to replay with the same store state must return the same result."""
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    t = datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC)
    store.record(_make_packet("kalshi", "KXBTCD-01", t))
    result1 = store.replay("kalshi", "KXBTCD-01")
    result2 = store.replay("kalshi", "KXBTCD-01")
    assert [p.snapshot_at for p in result1] == [p.snapshot_at for p in result2]


def test_replay_filters_by_market():
    """replay() must return only packets for the specified (venue_id, market_id) pair."""
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    t = datetime(2026, 3, 14, 12, 0, 0, tzinfo=UTC)
    store.record(_make_packet("kalshi", "MARKET-A", t))
    store.record(_make_packet("kalshi", "MARKET-B", t))
    replayed = store.replay("kalshi", "MARKET-A")
    assert len(replayed) == 1
    assert replayed[0].market_id == "MARKET-A"


def test_snapshot_at_must_be_utc_aware():
    """SnapshotStore.record() must raise ValueError if snapshot_at is timezone-naive."""
    from sharpedge_venue_adapters.protocol import CanonicalOrderBook, MarketStatePacket
    from sharpedge_venue_adapters.snapshot_store import SnapshotStore

    store = SnapshotStore()
    naive_ts = "2026-03-14T12:00:00"  # no timezone offset — invalid
    packet = MarketStatePacket(
        venue_id="kalshi",
        market_id="KXBTCD-01",
        snapshot_at=naive_ts,
        orderbook=CanonicalOrderBook(bids=(), asks=(), timestamp_utc=naive_ts),
        quotes=(),
    )
    with pytest.raises(ValueError):
        store.record(packet)
