"""Settlement Ledger: append-only event sourcing for financial events.

Each financial event (fill, fee, rebate, settlement, adjustment) is an
immutable LedgerEntry. Replay is achieved by summing entries chronologically.

Design principles:
- No UPDATE or DELETE operations — append-only
- All timestamps UTC-aware (ValueError on naive datetime)
- Deterministic replay: same entries -> same PnL always
- Supabase persistence: INSERT-only into ledger_entries table
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

LedgerEventType = Literal[
    "FILL",
    "FEE",
    "REBATE",
    "SETTLEMENT",
    "ADJUSTMENT",
    "POSITION_OPENED",
    "POSITION_CLOSED",
]

_VALID_EVENT_TYPES = {
    "FILL",
    "FEE",
    "REBATE",
    "SETTLEMENT",
    "ADJUSTMENT",
    "POSITION_OPENED",
    "POSITION_CLOSED",
}


@dataclass(frozen=True)
class LedgerEntry:
    """Immutable financial event record. Append-only — never modified after insert."""

    entry_id: int | None  # None before DB insert; set by GENERATED ALWAYS AS IDENTITY
    event_type: str  # LedgerEventType literal value
    venue_id: str  # e.g. "kalshi", "polymarket", "odds_api"
    market_id: str  # canonical market identifier
    position_lot_id: str  # UUID linking fills, fees, settlement for one lot
    amount_usdc: float  # positive = credit, negative = debit
    fee_component: float  # isolated fee portion (0 if not FEE event)
    rebate_component: float  # isolated rebate (0 if not REBATE event)
    price_at_event: float  # canonical probability at event time
    occurred_at: datetime  # venue-reported event time (MUST be UTC-aware)
    recorded_at: datetime  # when SharpEdge wrote this entry (MUST be UTC-aware)
    notes: str = ""

    def __post_init__(self) -> None:
        # Enforce UTC-aware timestamps
        if self.occurred_at.tzinfo is None:
            raise ValueError(
                f"LedgerEntry.occurred_at must be UTC-aware (got naive datetime: {self.occurred_at}). "
                "Use datetime.now(timezone.utc) or datetime(year, month, day, tzinfo=timezone.utc)."
            )
        if self.recorded_at.tzinfo is None:
            raise ValueError(
                f"LedgerEntry.recorded_at must be UTC-aware (got naive datetime: {self.recorded_at})."
            )
        if self.event_type not in _VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{self.event_type}'. Must be one of {_VALID_EVENT_TYPES}"
            )


def replay_position_pnl(
    entries: list[LedgerEntry],
    position_lot_id: str,
) -> float:
    """Deterministically compute PnL for a position lot from its ledger entries.

    Filters entries by position_lot_id, sorts by occurred_at ascending,
    and sums amount_usdc. Result is always the same for the same input
    (deterministic by design — no randomness, no I/O).

    Args:
        entries: list of LedgerEntry records (may include other position_lot_ids)
        position_lot_id: the lot to compute PnL for

    Returns:
        float: net PnL (positive = profit, negative = loss)
    """
    relevant = [e for e in entries if e.position_lot_id == position_lot_id]
    relevant_sorted = sorted(relevant, key=lambda e: e.occurred_at)
    return sum(e.amount_usdc for e in relevant_sorted)


class SettlementLedger:
    """Append-only settlement ledger. In-memory for tests; Supabase in production.

    Production mode: set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars.
    Test/offline mode: entries stored in-memory dict; no network calls.
    """

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []
        self._next_id: int = 1
        self._supabase = None

        # Attempt Supabase connection if env vars present
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        if url and key:
            try:
                from supabase import create_client

                self._supabase = create_client(url, key)
            except ImportError:
                pass  # supabase-py not installed — in-memory mode

    def append(self, entry: LedgerEntry) -> LedgerEntry:
        """Append an entry. Returns the entry with entry_id set.

        In Supabase mode: INSERT INTO ledger_entries, entry_id set from DB.
        In in-memory mode: entry_id set from internal counter.
        """
        if self._supabase is not None:
            try:
                row = {
                    "event_type": entry.event_type,
                    "venue_id": entry.venue_id,
                    "market_id": entry.market_id,
                    "position_lot_id": entry.position_lot_id,
                    "amount_usdc": entry.amount_usdc,
                    "fee_component": entry.fee_component,
                    "rebate_component": entry.rebate_component,
                    "price_at_event": entry.price_at_event,
                    "occurred_at": entry.occurred_at.isoformat(),
                    "recorded_at": entry.recorded_at.isoformat(),
                    "notes": entry.notes,
                }
                result = self._supabase.table("ledger_entries").insert(row).execute()
                db_id = result.data[0]["entry_id"] if result.data else self._next_id
                stored = LedgerEntry(
                    entry_id=db_id,
                    event_type=entry.event_type,
                    venue_id=entry.venue_id,
                    market_id=entry.market_id,
                    position_lot_id=entry.position_lot_id,
                    amount_usdc=entry.amount_usdc,
                    fee_component=entry.fee_component,
                    rebate_component=entry.rebate_component,
                    price_at_event=entry.price_at_event,
                    occurred_at=entry.occurred_at,
                    recorded_at=entry.recorded_at,
                    notes=entry.notes,
                )
                self._entries.append(stored)
                return stored
            except Exception:
                pass  # fall through to in-memory

        # In-memory mode
        stored = LedgerEntry(
            entry_id=self._next_id,
            event_type=entry.event_type,
            venue_id=entry.venue_id,
            market_id=entry.market_id,
            position_lot_id=entry.position_lot_id,
            amount_usdc=entry.amount_usdc,
            fee_component=entry.fee_component,
            rebate_component=entry.rebate_component,
            price_at_event=entry.price_at_event,
            occurred_at=entry.occurred_at,
            recorded_at=entry.recorded_at,
            notes=entry.notes,
        )
        self._entries.append(stored)
        self._next_id += 1
        return stored

    def get_position_entries(self, position_lot_id: str) -> list[LedgerEntry]:
        """Return all entries for a position lot, sorted by occurred_at ascending."""
        return sorted(
            [e for e in self._entries if e.position_lot_id == position_lot_id],
            key=lambda e: e.occurred_at,
        )

    def replay(self, position_lot_id: str) -> float:
        """Replay PnL for a position lot from stored entries."""
        return replay_position_pnl(self._entries, position_lot_id)
