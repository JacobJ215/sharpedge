"""KalshiAdapter: canonical wrapper over KalshiClient (transport tier)."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from sharpedge_venue_adapters.protocol import (
    CanonicalMarket,
    CanonicalOrderBook,
    CanonicalTrade,
    MarketLifecycleState,
    MarketStatePacket,
    SettlementState,
    VenueCapability,
    VenueFeeSchedule,
)

KALSHI_API_BASE = "https://trading-api.kalshi.com/trade-api/v2"
KALSHI_TAKER_FEE = 0.07


class KalshiAdapter:
    """Canonical adapter wrapping KalshiClient.

    Satisfies VenueAdapter protocol via structural subtyping (no inheritance).
    Offline mode (api_key=None) returns safe defaults without raising exceptions.
    """

    venue_id: str = "kalshi"
    capabilities: VenueCapability = VenueCapability(
        read_only=False,
        streaming_quotes=False,
        streaming_orderbook=False,
        execution_supported=True,
        maker_rewards=False,
        settlement_feed=True,
    )

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._client = None
        if api_key:
            try:
                from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig

                config = KalshiConfig(api_key=api_key)
                self._client = KalshiClient(config=config)
            except ImportError:
                self._client = None

    async def list_markets(self) -> list[CanonicalMarket]:
        """Return all open markets. Returns empty list in offline mode."""
        if self._client is None:
            return []
        try:
            raw = await self._client.get_markets()
            return [self._to_canonical(m) for m in raw]
        except Exception:
            return []

    def _to_canonical(self, m) -> CanonicalMarket:
        """Map a KalshiMarket to CanonicalMarket.

        NOTE: yes_bid and yes_ask from KalshiMarket are already float probability
        (0.0-1.0) — _parse_market() handles cents->float conversion internally.
        Do NOT divide by 100 again here.
        """
        state = (
            MarketLifecycleState.SETTLED if m.result in ("yes", "no") else MarketLifecycleState.OPEN
        )
        return CanonicalMarket(
            venue_id="kalshi",
            market_id=m.ticker,
            title=m.title,
            state=state,
            yes_bid=float(m.yes_bid) if m.yes_bid is not None else 0.0,
            yes_ask=float(m.yes_ask) if m.yes_ask is not None else 0.0,
            volume=int(m.volume) if m.volume is not None else 0,
            close_time_utc=str(m.close_time) if m.close_time else "",
        )

    async def get_market_details(self, market_id: str) -> CanonicalMarket | None:
        """Return details for a single market by ticker, or None if not found."""
        markets = await self.list_markets()
        return next((m for m in markets if m.market_id == market_id), None)

    async def get_orderbook(self, market_id: str) -> CanonicalOrderBook:
        """Return orderbook for a market. Returns empty book in offline mode."""
        if self._api_key is None:
            return CanonicalOrderBook(
                bids=(),
                asks=(),
                timestamp_utc=datetime.now(UTC).isoformat(),
            )
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{KALSHI_API_BASE}/markets/{market_id}/orderbook",
                    headers={"KALSHI-ACCESS-KEY": self._api_key},
                )
                resp.raise_for_status()
                data = resp.json()
                orderbook = data.get("orderbook", {})
                return CanonicalOrderBook(
                    bids=tuple(orderbook.get("yes", [])),
                    asks=tuple(orderbook.get("no", [])),
                    timestamp_utc=datetime.now(UTC).isoformat(),
                )
        except Exception:
            return CanonicalOrderBook(
                bids=(),
                asks=(),
                timestamp_utc=datetime.now(UTC).isoformat(),
            )

    async def get_trades(self, market_id: str, limit: int = 100) -> list[CanonicalTrade]:
        """Return recent trades. Empty list in Phase 6 (live trade endpoint not wired)."""
        return []

    async def get_historical_snapshots(
        self,
        market_id: str,
        start_utc: str,
        end_utc: str,
    ) -> list[MarketStatePacket]:
        """Not yet implemented — Kalshi candlestick API not confirmed."""
        raise NotImplementedError(
            "historical data endpoint not confirmed"
            " — implement after verifying Kalshi candlestick API"
        )

    async def get_fees_and_limits(self) -> VenueFeeSchedule:
        """Return Kalshi fee schedule: 7% taker, 0% maker."""
        return VenueFeeSchedule(
            venue_id="kalshi",
            maker_fee_rate=0.0,
            taker_fee_rate=KALSHI_TAKER_FEE,
            expected_quote_refresh_seconds=5,
        )

    async def get_settlement_state(self, market_id: str) -> SettlementState:
        """Return settlement state based on market result field."""
        market = await self.get_market_details(market_id)
        if market is None:
            return SettlementState(
                market_id=market_id,
                outcome=None,
                is_settled=False,
            )
        return SettlementState(
            market_id=market_id,
            outcome=None,  # TODO: map from market.result when live client available
            is_settled=market.state == MarketLifecycleState.SETTLED,
        )
