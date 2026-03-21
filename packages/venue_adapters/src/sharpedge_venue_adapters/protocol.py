"""Canonical typed contracts for multi-venue adapter layer.

All types defined here are the interface foundation that adapter implementations
(Waves 2-3) build against. Zero external dependencies beyond stdlib and typing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable


class InvalidTransitionError(ValueError):
    """Raised when a MarketLifecycleState transition is not permitted."""

    pass


class MarketLifecycleState(Enum):
    """Lifecycle states for prediction market contracts."""

    OPEN = "open"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    SETTLED = "settled"
    CANCELLED = "cancelled"

    def valid_next(self) -> set[MarketLifecycleState]:
        """Return the set of valid next states from this state."""
        return _VALID_TRANSITIONS.get(self, set())

    def transition_to(self, new_state: MarketLifecycleState) -> MarketLifecycleState:
        """Transition to new_state, raising InvalidTransitionError if not allowed."""
        if new_state not in self.valid_next():
            raise InvalidTransitionError(f"Invalid transition: {self.value} -> {new_state.value}")
        return new_state


# Transition table: defines allowed state machine edges
_VALID_TRANSITIONS: dict[MarketLifecycleState, set[MarketLifecycleState]] = {
    MarketLifecycleState.OPEN: {
        MarketLifecycleState.SUSPENDED,
        MarketLifecycleState.CLOSED,
        MarketLifecycleState.CANCELLED,
    },
    MarketLifecycleState.SUSPENDED: {
        MarketLifecycleState.OPEN,
        MarketLifecycleState.CLOSED,
        MarketLifecycleState.CANCELLED,
    },
    MarketLifecycleState.CLOSED: {
        MarketLifecycleState.SETTLED,
        MarketLifecycleState.CANCELLED,
    },
    MarketLifecycleState.SETTLED: set(),
    MarketLifecycleState.CANCELLED: set(),
}


@dataclass(frozen=True)
class VenueCapability:
    """Capability flags for a venue adapter."""

    read_only: bool
    streaming_quotes: bool
    streaming_orderbook: bool
    execution_supported: bool
    maker_rewards: bool
    settlement_feed: bool


@dataclass(frozen=True)
class CanonicalMarket:
    """Normalized market representation across all venues."""

    venue_id: str
    market_id: str
    title: str
    state: MarketLifecycleState
    yes_bid: float
    yes_ask: float
    volume: float
    close_time_utc: str


@dataclass(frozen=True)
class CanonicalOrderBook:
    """Normalized orderbook with probability-scale prices."""

    bids: tuple  # list[dict] with "price" and "size" keys
    asks: tuple  # list[dict] with "price" and "size" keys
    timestamp_utc: str


@dataclass(frozen=True)
class CanonicalQuote:
    """Normalized single-outcome quote with probability-scale prices."""

    venue_id: str
    market_id: str
    outcome_id: str
    raw_bid: float
    raw_ask: float
    raw_format: str  # "probability" | "american" | "cents" | "decimal"
    fair_prob: float
    mid_prob: float
    spread_prob: float
    maker_fee_rate: float
    taker_fee_rate: float
    timestamp_utc: str


@dataclass(frozen=True)
class CanonicalTrade:
    """Normalized executed trade record."""

    venue_id: str
    market_id: str
    price: float
    size: float
    side: str  # "buy" | "sell"
    timestamp_utc: str


@dataclass(frozen=True)
class VenueFeeSchedule:
    """Fee parameters for a venue."""

    venue_id: str
    maker_fee_rate: float
    taker_fee_rate: float
    expected_quote_refresh_seconds: int


@dataclass(frozen=True)
class SettlementState:
    """Settlement outcome for a market."""

    market_id: str
    outcome: str | None  # "yes" | "no" | None if unresolved
    is_settled: bool


@dataclass(frozen=True)
class MarketStatePacket:
    """Snapshot bundle for a single market at a point in time."""

    venue_id: str
    market_id: str
    snapshot_at: str
    orderbook: CanonicalOrderBook | None
    quotes: tuple  # tuple[CanonicalQuote, ...]


@runtime_checkable
class VenueAdapter(Protocol):
    """Protocol that all venue adapter implementations must satisfy.

    All methods are async. Implementations provide venue-specific logic
    behind this stable interface. Use isinstance(obj, VenueAdapter) for
    runtime structural checks.
    """

    venue_id: str
    capabilities: VenueCapability

    async def list_markets(self) -> list[CanonicalMarket]:
        """Return all active markets for this venue."""
        ...

    async def get_market_details(self, market_id: str) -> CanonicalMarket | None:
        """Return full details for a single market, or None if not found."""
        ...

    async def get_orderbook(self, market_id: str) -> CanonicalOrderBook | None:
        """Return current orderbook for a market, or None if unavailable."""
        ...

    async def get_trades(self, market_id: str, limit: int = 100) -> list[CanonicalTrade]:
        """Return recent trades for a market."""
        ...

    async def get_historical_snapshots(
        self,
        market_id: str,
        start_utc: str,
        end_utc: str,
    ) -> list[MarketStatePacket]:
        """Return historical snapshots for a market between two timestamps."""
        ...

    async def get_fees_and_limits(self) -> VenueFeeSchedule:
        """Return current fee schedule for this venue."""
        ...

    async def get_settlement_state(self, market_id: str) -> SettlementState:
        """Return settlement outcome for a market."""
        ...


__all__ = [
    "CanonicalMarket",
    "CanonicalOrderBook",
    "CanonicalQuote",
    "CanonicalTrade",
    "InvalidTransitionError",
    "MarketLifecycleState",
    "MarketStatePacket",
    "SettlementState",
    "VenueAdapter",
    "VenueCapability",
    "VenueFeeSchedule",
]
