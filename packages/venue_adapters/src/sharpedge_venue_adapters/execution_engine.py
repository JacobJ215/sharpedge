"""Shadow Execution Engine: paper-trading layer for Kalshi CLOB order submission.

All order processing is simulated (shadow mode) — no real capital is deployed.
The engine enforces per-market and per-day exposure limits via guard objects and
records every accepted intent in an append-only ShadowLedger.

Design principles:
- Shadow mode only — ENABLE_KALSHI_EXECUTION must NOT be set for paper trading
- All timestamps UTC-aware (ValueError on naive datetime)
- Per-market and per-day exposure guards prevent over-commitment
- ShadowLedger is append-only (no UPDATE or DELETE)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrderIntent:
    """Represents a trading intent before execution decision is made."""

    market_id: str
    predicted_edge: float
    fair_prob: float
    kelly_fraction: float
    bankroll: float
    created_at: datetime

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("OrderIntent.created_at must be UTC-aware")


@dataclass(frozen=True)
class ShadowLedgerEntry:
    """Immutable record of an accepted shadow order intent."""

    entry_id: int | None
    market_id: str
    predicted_edge: float
    kelly_sized_amount: float
    timestamp: datetime

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("ShadowLedgerEntry.timestamp must be UTC-aware")


class ShadowLedger:
    """Append-only ledger for shadow execution entries."""

    def __init__(self) -> None:
        self._entries: list[ShadowLedgerEntry] = []

    def append(self, entry: ShadowLedgerEntry) -> ShadowLedgerEntry:
        """Append entry to the shadow ledger and return it."""
        raise NotImplementedError("ShadowLedger.append not yet implemented")

    @property
    def entries(self) -> list[ShadowLedgerEntry]:
        """Return a copy of all ledger entries."""
        return list(self._entries)


class MarketExposureGuard:
    """Enforces per-market stake exposure limit."""

    def __init__(self, max_market_exposure: float) -> None:
        self._max_market_exposure = max_market_exposure
        self._committed: dict[str, float] = {}

    def would_breach(self, market_id: str, stake: float) -> bool:
        """Return True if adding stake to market_id would exceed the per-market cap."""
        raise NotImplementedError("MarketExposureGuard.would_breach not yet implemented")

    def commit(self, market_id: str, stake: float) -> None:
        """Record that stake has been committed to market_id."""
        raise NotImplementedError("MarketExposureGuard.commit not yet implemented")


class DayExposureGuard:
    """Enforces per-day total stake exposure limit with midnight UTC reset."""

    def __init__(self, max_day_exposure: float) -> None:
        self._max_day_exposure = max_day_exposure
        self._day_stake_total: float = 0.0
        self._current_day: int | None = None

    def would_breach(self, stake: float) -> bool:
        """Return True if adding stake would exceed the daily cap."""
        raise NotImplementedError("DayExposureGuard.would_breach not yet implemented")

    def commit(self, stake: float) -> None:
        """Record that stake has been committed for today."""
        raise NotImplementedError("DayExposureGuard.commit not yet implemented")

    @property
    def day_stake(self) -> float:
        """Return cumulative stake committed today."""
        raise NotImplementedError("DayExposureGuard.day_stake not yet implemented")


class ShadowExecutionEngine:
    """Orchestrates shadow order processing with exposure guard enforcement."""

    def __init__(self, max_market_exposure: float, max_day_exposure: float) -> None:
        self._market_guard = MarketExposureGuard(max_market_exposure)
        self._day_guard = DayExposureGuard(max_day_exposure)
        self._ledger = ShadowLedger()

    def process_intent(self, intent: OrderIntent) -> ShadowLedgerEntry | None:
        """Evaluate an order intent, apply guards, write to shadow ledger if accepted.

        Returns ShadowLedgerEntry on acceptance, None if any guard rejects.
        """
        raise NotImplementedError("ShadowExecutionEngine.process_intent not yet implemented")

    @property
    def shadow_ledger(self) -> ShadowLedger:
        """Return the underlying shadow ledger."""
        return self._ledger
