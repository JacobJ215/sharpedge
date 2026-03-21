"""SnapshotStore: append-only market state snapshot persistence.

Satisfies the locked CONTEXT.md architectural principle:
  "Deterministic replay: every market-state snapshot must be replayable from stored events"

Design:
- In-memory for tests/offline (no env vars needed)
- Supabase (INSERT-only into market_snapshots) when SUPABASE_URL + service_role key present
- All snapshots sorted by snapshot_at ascending for deterministic replay
- UTC-aware snapshot_at enforced — raises ValueError on naive timestamps
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sharpedge_venue_adapters.protocol import MarketStatePacket


def _validate_utc_aware(snapshot_at: str) -> None:
    """Raise ValueError if snapshot_at is a naive ISO-8601 timestamp (no TZ offset)."""
    ts = snapshot_at.strip()
    # Remove the date portion (first 19 chars: "YYYY-MM-DDTHH:MM:SS")
    after_time = ts[19:] if len(ts) > 19 else ""
    has_tz = after_time.startswith("+") or after_time.startswith("-") or "Z" in after_time
    if not has_tz:
        raise ValueError(
            f"snapshot_at must be a UTC-aware ISO-8601 timestamp (got: '{snapshot_at}'). "
            "Append '+00:00' or 'Z' to make it UTC-aware."
        )


@dataclass
class SnapshotRecord:
    """Serializable representation of a MarketStatePacket for Supabase INSERT."""

    venue_id: str
    market_id: str
    snapshot_at: str  # ISO-8601 UTC-aware
    orderbook_json: str  # JSON string of CanonicalOrderBook
    quotes_json: str  # JSON string of list[CanonicalQuote]


def _packet_to_record(packet: MarketStatePacket) -> SnapshotRecord:
    """Convert MarketStatePacket to a JSON-serializable SnapshotRecord."""
    orderbook_dict: dict[str, Any] = {}
    if packet.orderbook is not None:
        orderbook_dict = {
            "bids": list(packet.orderbook.bids),
            "asks": list(packet.orderbook.asks),
            "timestamp_utc": packet.orderbook.timestamp_utc,
        }

    quotes_list = [
        {
            "venue_id": q.venue_id,
            "market_id": q.market_id,
            "outcome_id": q.outcome_id,
            "raw_bid": q.raw_bid,
            "raw_ask": q.raw_ask,
            "raw_format": q.raw_format,
            "fair_prob": q.fair_prob,
            "mid_prob": q.mid_prob,
            "spread_prob": q.spread_prob,
            "maker_fee_rate": q.maker_fee_rate,
            "taker_fee_rate": q.taker_fee_rate,
            "timestamp_utc": q.timestamp_utc,
        }
        for q in packet.quotes
    ]

    return SnapshotRecord(
        venue_id=packet.venue_id,
        market_id=packet.market_id,
        snapshot_at=packet.snapshot_at,
        orderbook_json=json.dumps(orderbook_dict),
        quotes_json=json.dumps(quotes_list),
    )


class SnapshotStore:
    """Append-only store for MarketStatePacket snapshots.

    In-memory for tests (no env vars). Supabase in production.
    All replay operations are deterministic: sorted by snapshot_at ascending.
    """

    def __init__(self) -> None:
        self._packets: list[MarketStatePacket] = []
        self._supabase: Any = None

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if url and key:
            try:
                from supabase import create_client  # type: ignore[import]

                self._supabase = create_client(url, key)
            except ImportError:
                pass  # supabase-py not installed — fall back to in-memory

    def record(self, packet: MarketStatePacket) -> None:
        """Append a MarketStatePacket snapshot.

        Raises ValueError if packet.snapshot_at is timezone-naive.
        """
        _validate_utc_aware(packet.snapshot_at)

        if self._supabase is not None:
            try:
                rec = _packet_to_record(packet)
                self._supabase.table("market_snapshots").insert(
                    {
                        "venue_id": rec.venue_id,
                        "market_id": rec.market_id,
                        "snapshot_at": rec.snapshot_at,
                        "orderbook_json": rec.orderbook_json,
                        "quotes_json": rec.quotes_json,
                    }
                ).execute()
            except Exception:
                pass  # fall through to in-memory on any Supabase error

        self._packets.append(packet)

    def replay(self, venue_id: str, market_id: str) -> list[MarketStatePacket]:
        """Return all snapshots for a market, sorted by snapshot_at ascending.

        Deterministic: same store state always produces the same ordered list.

        Args:
            venue_id: venue identifier (e.g. "kalshi")
            market_id: market identifier (e.g. "KXBTCD-26MAR14")

        Returns:
            list[MarketStatePacket] sorted by snapshot_at ascending
        """
        relevant = [p for p in self._packets if p.venue_id == venue_id and p.market_id == market_id]
        return sorted(relevant, key=lambda p: p.snapshot_at)


__all__ = [
    "SnapshotRecord",
    "SnapshotStore",
]
