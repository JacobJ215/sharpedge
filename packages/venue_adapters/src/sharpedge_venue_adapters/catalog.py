"""MarketCatalog: in-memory lifecycle state machine for canonical markets."""
from __future__ import annotations

from sharpedge_venue_adapters.protocol import (
    MarketLifecycleState,
    InvalidTransitionError,
)

_STATUS_MAP: dict[str, MarketLifecycleState] = {
    "open": MarketLifecycleState.OPEN,
    "suspended": MarketLifecycleState.SUSPENDED,
    "closed": MarketLifecycleState.CLOSED,
    "settled": MarketLifecycleState.SETTLED,
    "cancelled": MarketLifecycleState.CANCELLED,
}

# Re-export for callers who import from catalog
__all__ = ["MarketCatalog", "MarketLifecycleState", "InvalidTransitionError"]


class MarketCatalog:
    """In-memory market catalog with lifecycle state enforcement.

    Supabase persistence is deferred — tests and offline use in-memory dict.
    """

    def __init__(self) -> None:
        self._markets: dict[tuple[str, str], dict] = {}

    def upsert(self, market_dict: dict) -> None:
        """Insert or update a market entry.

        Reads 'status' field (string) and converts to MarketLifecycleState.
        Falls back to OPEN if status is absent or unrecognized.
        """
        key = (market_dict["venue_id"], market_dict["market_id"])
        state_str = market_dict.get("status", "open").lower()
        state = _STATUS_MAP.get(state_str, MarketLifecycleState.OPEN)
        self._markets[key] = {**market_dict, "state": state}

    def get(self, venue_id: str, market_id: str) -> dict | None:
        """Return a stored market dict, or None if not found."""
        return self._markets.get((venue_id, market_id))

    def transition(
        self,
        venue_id: str,
        market_id: str,
        new_state: MarketLifecycleState,
    ) -> None:
        """Update market state, enforcing valid transition rules.

        Raises:
            KeyError: if market not found in catalog.
            InvalidTransitionError: if transition is not permitted.
        """
        key = (venue_id, market_id)
        entry = self._markets.get(key)
        if entry is None:
            raise KeyError(f"Market not found: {venue_id}/{market_id}")
        current: MarketLifecycleState = entry["state"]
        entry["state"] = current.transition_to(new_state)

    def list(self, status: MarketLifecycleState | None = None) -> list[dict]:
        """Return all markets, optionally filtered by lifecycle state."""
        markets = list(self._markets.values())
        if status is not None:
            markets = [m for m in markets if m["state"] == status]
        return markets
