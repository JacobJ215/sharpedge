"""PolymarketAdapter: canonical wrapper over PolymarketClient (transport tier)."""
from __future__ import annotations

import httpx
from datetime import datetime, timezone

from sharpedge_venue_adapters.protocol import (
    VenueCapability,
    CanonicalMarket,
    CanonicalOrderBook,
    CanonicalTrade,
    VenueFeeSchedule,
    SettlementState,
    MarketStatePacket,
    MarketLifecycleState,
)

POLYMARKET_CLOB_BASE = "https://clob.polymarket.com"


class PolymarketAdapter:
    """Canonical adapter wrapping PolymarketClient.

    Satisfies VenueAdapter protocol via structural subtyping (no inheritance).
    Read-only in Phase 6 — no EIP-712 signing; maker rewards apply to liquidity provision.
    Prices are already 0.0–1.0 probability scale; no conversion needed.
    """

    venue_id: str = "polymarket"
    capabilities: VenueCapability = VenueCapability(
        read_only=True,
        streaming_quotes=False,
        streaming_orderbook=False,
        execution_supported=False,
        maker_rewards=True,
        settlement_feed=False,
    )

    def __init__(self) -> None:
        self._client = None
        try:
            from sharpedge_feeds.polymarket_client import PolymarketClient, PolymarketConfig
            self._client = PolymarketClient(config=PolymarketConfig())
        except ImportError:
            self._client = None

    async def list_markets(self) -> list[CanonicalMarket]:
        """Return all active markets. Returns empty list when client unavailable."""
        if self._client is None:
            return []
        try:
            raw = await self._client.get_markets()
            return [self._to_canonical(m) for m in raw if m is not None]
        except Exception:
            return []

    def _to_canonical(self, m) -> CanonicalMarket:
        """Map a PolymarketMarket to CanonicalMarket.

        For binary markets, use YES outcome price as bid, infer ask from NO outcome.
        Prices are already 0.0–1.0 probability scale from PolymarketClient.
        """
        yes_price = 0.5
        no_price = 0.5
        for outcome in getattr(m, "outcomes", []):
            name = str(getattr(outcome, "outcome", "")).lower()
            price = float(getattr(outcome, "price", 0.5))
            if name == "yes":
                yes_price = price
            elif name == "no":
                no_price = price

        # yes_bid = YES price, yes_ask = 1 - NO price (complement)
        yes_bid = yes_price
        yes_ask = 1.0 - no_price

        state = MarketLifecycleState.OPEN
        if getattr(m, "closed", False):
            state = MarketLifecycleState.CLOSED

        return CanonicalMarket(
            venue_id="polymarket",
            market_id=getattr(m, "condition_id", ""),
            title=getattr(m, "question", ""),
            state=state,
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            volume=int(getattr(m, "volume", 0) or 0),
            close_time_utc=(
                str(m.end_date) if getattr(m, "end_date", None) else ""
            ),
        )

    async def get_market_details(self, market_id: str) -> CanonicalMarket | None:
        """Return details for a single market by condition_id, or None if not found."""
        markets = await self.list_markets()
        return next((m for m in markets if m.market_id == market_id), None)

    async def get_orderbook(self, market_id: str) -> CanonicalOrderBook:
        """Return CLOB orderbook for a token_id. Falls back to empty on error.

        market_id here is treated as a CLOB token_id for per-outcome orderbook queries.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{POLYMARKET_CLOB_BASE}/book",
                    params={"token_id": market_id},
                )
                resp.raise_for_status()
                data = resp.json()
                return CanonicalOrderBook(
                    bids=tuple(data.get("bids", [])),
                    asks=tuple(data.get("asks", [])),
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                )
        except Exception:
            return CanonicalOrderBook(
                bids=(),
                asks=(),
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

    async def get_trades(self, market_id: str, limit: int = 100) -> list[CanonicalTrade]:
        """Return recent trades. Empty list in Phase 6 (CLOB trade history not wired)."""
        return []

    async def get_historical_snapshots(
        self,
        market_id: str,
        start_utc: str,
        end_utc: str,
    ) -> list[MarketStatePacket]:
        """Return empty list — Polymarket historical data deferred to Phase 7."""
        return []

    async def get_fees_and_limits(self) -> VenueFeeSchedule:
        """Return Polymarket fee schedule: no direct fees; maker rewards apply."""
        return VenueFeeSchedule(
            venue_id="polymarket",
            maker_fee_rate=0.0,
            taker_fee_rate=0.0,
            expected_quote_refresh_seconds=30,
        )

    async def get_settlement_state(self, market_id: str) -> SettlementState:
        """Return settlement state. Phase 6 read-only — Gamma API integration deferred."""
        return SettlementState(
            market_id=market_id,
            outcome=None,
            is_settled=False,
        )
