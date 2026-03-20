"""Shadow execution engine — enforces exposure limits and writes ShadowLedger entries.

Phase 12: Optionally submits live CLOB orders when ENABLE_KALSHI_EXECUTION=true.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sharpedge_feeds.kalshi_client import KalshiClient

from sharpedge_venue_adapters.ledger import LedgerEntry, SettlementLedger

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"executed", "canceled"})


# ---------------------------------------------------------------------------
# Live order poller
# ---------------------------------------------------------------------------


class LiveOrderPoller:
    """Polls Kalshi order status until terminal, then writes to SettlementLedger."""

    async def poll_until_terminal(
        self,
        order_id: str,
        market_id: str,
        ticker: str,
        position_lot_id: str,
        stake_usd: float,
        submitted_price_cents: int,
        kalshi_client: "KalshiClient",
        settlement_ledger: SettlementLedger,
        interval_s: float = 5.0,
        max_attempts: int = 60,
    ) -> LedgerEntry | None:
        """Poll until terminal status, write fill or cancel entry. Returns LedgerEntry."""
        for attempt in range(max_attempts):
            await asyncio.sleep(interval_s)
            order = await kalshi_client.get_order(order_id)
            if order is None:
                continue
            if order.status not in TERMINAL_STATUSES:
                continue
            now = datetime.now(timezone.utc)
            if order.status == "executed":
                entry = LedgerEntry(
                    entry_id=None,
                    event_type="FILL",
                    venue_id="kalshi",
                    market_id=market_id,
                    position_lot_id=position_lot_id,
                    amount_usdc=0.0,
                    fee_component=0.0,
                    rebate_component=0.0,
                    price_at_event=order.yes_price / 100.0,
                    occurred_at=now,
                    recorded_at=now,
                    notes=f"order_id={order_id} filled qty={order.count}",
                )
            else:  # canceled
                entry = LedgerEntry(
                    entry_id=None,
                    event_type="ADJUSTMENT",
                    venue_id="kalshi",
                    market_id=market_id,
                    position_lot_id=position_lot_id,
                    amount_usdc=+stake_usd,
                    fee_component=0.0,
                    rebate_component=0.0,
                    price_at_event=submitted_price_cents / 100.0,
                    occurred_at=now,
                    recorded_at=now,
                    notes=f"order_id={order_id} canceled reason=exchange",
                )
            return settlement_ledger.append(entry)
        # max_attempts exhausted
        now = datetime.now(timezone.utc)
        entry = LedgerEntry(
            entry_id=None,
            event_type="ADJUSTMENT",
            venue_id="kalshi",
            market_id=market_id,
            position_lot_id=position_lot_id,
            amount_usdc=+stake_usd,
            fee_component=0.0,
            rebate_component=0.0,
            price_at_event=submitted_price_cents / 100.0,
            occurred_at=now,
            recorded_at=now,
            notes=f"order_id={order_id} canceled reason=order not found after max_attempts",
        )
        return settlement_ledger.append(entry)


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderIntent:
    """A pre-execution signal from the PM edge scanner or risk agent."""
    market_id: str
    predicted_edge: float       # model_prob - market_prob as fraction (e.g. 0.05)
    fair_prob: float            # model's calibrated probability
    kelly_fraction: float       # fractional Kelly multiplier (e.g. 0.25)
    bankroll: float             # current bankroll in USD
    created_at: datetime        # UTC-aware

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None:
            raise ValueError("OrderIntent.created_at must be UTC-aware")


@dataclass(frozen=True)
class ShadowLedgerEntry:
    """One accepted signal written to the shadow ledger."""
    entry_id: Optional[int]
    market_id: str
    predicted_edge: float       # fraction
    kelly_sized_amount: float   # USD stake = bankroll * kelly_fraction
    timestamp: datetime         # UTC-aware
    position_lot_id: str = ""   # UUID linking SettlementLedger entries in live mode; "" in shadow

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("ShadowLedgerEntry.timestamp must be UTC-aware")


# ---------------------------------------------------------------------------
# Shadow ledger (in-memory; Supabase persistence is a Phase 14 extension)
# ---------------------------------------------------------------------------

class ShadowLedger:
    """Append-only in-memory store for ShadowLedgerEntry records."""

    def __init__(self) -> None:
        self._entries: list[ShadowLedgerEntry] = []

    def append(self, entry: ShadowLedgerEntry) -> ShadowLedgerEntry:
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list[ShadowLedgerEntry]:
        return list(self._entries)


# ---------------------------------------------------------------------------
# Exposure guards
# ---------------------------------------------------------------------------

class MarketExposureGuard:
    """Rejects intents that would push a single market over the dollar cap."""

    def __init__(self, max_market_exposure: float) -> None:
        self._max = max_market_exposure
        self._market_stake: dict[str, float] = {}

    def would_breach(self, market_id: str, stake: float) -> bool:
        current = self._market_stake.get(market_id, 0.0)
        return (current + stake) > self._max

    def commit(self, market_id: str, stake: float) -> None:
        self._market_stake[market_id] = self._market_stake.get(market_id, 0.0) + stake


class DayExposureGuard:
    """Rejects intents that would push cumulative day stake over the dollar cap.

    Resets automatically at UTC midnight — same pattern as CircuitBreakerState
    in sharpedge_trading.agents.risk_agent.
    """

    def __init__(self, max_day_exposure: float) -> None:
        self._max = max_day_exposure
        self._day_stake: float = 0.0
        self._reset_date: str = ""  # YYYY-MM-DD UTC

    def _maybe_reset(self) -> None:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._reset_date:
            self._day_stake = 0.0
            self._reset_date = today

    def would_breach(self, stake: float) -> bool:
        self._maybe_reset()
        return (self._day_stake + stake) > self._max

    def commit(self, stake: float) -> None:
        self._maybe_reset()
        self._day_stake += stake

    @property
    def day_stake(self) -> float:
        self._maybe_reset()
        return self._day_stake


# ---------------------------------------------------------------------------
# Shadow execution engine
# ---------------------------------------------------------------------------

class ShadowExecutionEngine:
    """Enforces exposure limits and records accepted signals to ShadowLedger.

    Shadow mode (kalshi_client=None): records intents to ShadowLedger only.
    Live mode (kalshi_client provided): additionally submits CLOB orders via
    KalshiClient and tracks fills/cancels in SettlementLedger (EXEC-03, EXEC-05).

    Default limits are read from env vars with fallbacks:
      SHADOW_MAX_MARKET_EXPOSURE  (default: 500.0 USD)
      SHADOW_MAX_DAY_EXPOSURE     (default: 2000.0 USD)
    """

    def __init__(
        self,
        max_market_exposure: float,
        max_day_exposure: float,
        kalshi_client=None,           # None = shadow mode
        settlement_ledger: SettlementLedger | None = None,
        poll_interval_seconds: float = 5.0,
        poll_max_attempts: int = 60,
    ) -> None:
        self._market_guard = MarketExposureGuard(max_market_exposure)
        self._day_guard = DayExposureGuard(max_day_exposure)
        self._ledger = ShadowLedger()
        self._kalshi_client = kalshi_client
        self._settlement_ledger = settlement_ledger
        self._poll_interval = poll_interval_seconds
        self._poll_max_attempts = poll_max_attempts
        self._poller = LiveOrderPoller()

    @classmethod
    def from_env(cls) -> "ShadowExecutionEngine":
        """Construct with limits from environment variables.

        When ENABLE_KALSHI_EXECUTION=true, wires a live KalshiClient +
        SettlementLedger using KALSHI_API_KEY and KALSHI_PRIVATE_KEY_PEM.
        """
        max_market = float(os.environ.get("SHADOW_MAX_MARKET_EXPOSURE", "500.0"))
        max_day = float(os.environ.get("SHADOW_MAX_DAY_EXPOSURE", "2000.0"))
        kalshi_client = None
        settlement_ledger = None
        if os.environ.get("ENABLE_KALSHI_EXECUTION", "").lower() == "true":
            from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig
            api_key = os.environ.get("KALSHI_API_KEY", "")
            private_key_pem = os.environ.get("KALSHI_PRIVATE_KEY_PEM")
            config = KalshiConfig(api_key=api_key, private_key_pem=private_key_pem)
            kalshi_client = KalshiClient(config)
            settlement_ledger = SettlementLedger()
        return cls(
            max_market_exposure=max_market,
            max_day_exposure=max_day,
            kalshi_client=kalshi_client,
            settlement_ledger=settlement_ledger,
        )

    async def process_intent(self, intent: OrderIntent) -> Optional[ShadowLedgerEntry]:
        """Check exposure limits, write to ShadowLedger, and (in live mode) submit order.

        Returns ShadowLedgerEntry on acceptance, None on rejection.
        Rejection always happens BEFORE any ledger write (EXEC-04).
        """
        stake = intent.kelly_fraction * intent.bankroll

        # Gate 1: per-market dollar cap
        if self._market_guard.would_breach(intent.market_id, stake):
            logger.warning(
                "Per-market limit breach for %s (stake=%.2f) — intent rejected",
                intent.market_id,
                stake,
            )
            return None

        # Gate 2: per-day cumulative cap
        if self._day_guard.would_breach(stake):
            logger.warning(
                "Per-day limit breach (stake=%.2f, market=%s) — intent rejected",
                stake,
                intent.market_id,
            )
            return None

        # Accept: commit limits then write shadow ledger
        self._market_guard.commit(intent.market_id, stake)
        self._day_guard.commit(stake)

        # Live mode: submit CLOB order, write POSITION_OPENED, then poll for fill/cancel
        if self._kalshi_client is not None and self._settlement_ledger is not None:
            lot_id = str(uuid.uuid4())
            yes_price_cents = int(intent.fair_prob * 100)
            contracts = max(1, int(stake / (yes_price_cents / 100.0))) if yes_price_cents > 0 else 1

            order = await self._kalshi_client.create_order(
                ticker=intent.market_id,
                action="buy",
                side="yes",
                order_type="limit",
                count=contracts,
                yes_price=yes_price_cents,
            )

            now = datetime.now(timezone.utc)
            self._settlement_ledger.append(LedgerEntry(
                entry_id=None,
                event_type="POSITION_OPENED",
                venue_id="kalshi",
                market_id=intent.market_id,
                position_lot_id=lot_id,
                amount_usdc=-stake,
                fee_component=0.0,
                rebate_component=0.0,
                price_at_event=yes_price_cents / 100.0,
                occurred_at=now,
                recorded_at=now,
                notes=f"order_id={order.order_id}",
            ))

            await self._poller.poll_until_terminal(
                order_id=order.order_id,
                market_id=intent.market_id,
                ticker=intent.market_id,
                position_lot_id=lot_id,
                stake_usd=stake,
                submitted_price_cents=yes_price_cents,
                kalshi_client=self._kalshi_client,
                settlement_ledger=self._settlement_ledger,
                interval_s=self._poll_interval,
                max_attempts=self._poll_max_attempts,
            )

            shadow_entry = ShadowLedgerEntry(
                entry_id=None,
                market_id=intent.market_id,
                predicted_edge=intent.predicted_edge,
                kelly_sized_amount=stake,
                timestamp=intent.created_at,
                position_lot_id=lot_id,
            )
        else:
            shadow_entry = ShadowLedgerEntry(
                entry_id=None,
                market_id=intent.market_id,
                predicted_edge=intent.predicted_edge,
                kelly_sized_amount=stake,
                timestamp=intent.created_at,
            )

        return self._ledger.append(shadow_entry)

    @property
    def shadow_ledger(self) -> ShadowLedger:
        return self._ledger
