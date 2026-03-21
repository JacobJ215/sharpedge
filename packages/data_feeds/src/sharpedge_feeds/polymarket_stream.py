"""Real-time WebSocket client for Polymarket CLOB market data.

Subscribes to the `book` channel which pushes full orderbook snapshots
on every change. We extract the best ask (lowest ask price) for each
subscribed token to power arb detection.

Polymarket CLOB WS:
  wss://ws-subscriptions-clob.polymarket.com/ws/market
  No auth required for public market data.
  Subscribe: {"type": "subscribe", "assets_ids": [...]}
  Message format: {"event_type": "book", "asset_id": "...",
                   "bids": [{"price": "0.49", "size": "1500"}, ...],
                   "asks": [{"price": "0.51", "size": "2000"}, ...]}

  Also handles price_change events for lightweight mid-price updates:
  {"event_type": "price_change", "asset_id": "...", "price": "0.50", ...}
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import websockets
import websockets.exceptions

logger = logging.getLogger(__name__)

_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"


@dataclass
class PolyTick:
    """Real-time price tick from Polymarket CLOB."""

    token_id: str
    best_bid: float   # 0-1; highest bid (price a buyer will pay)
    best_ask: float   # 0-1; lowest ask (price to buy at)
    mid: float        # (bid + ask) / 2
    timestamp: float = field(default_factory=time.time)


PolyTickCallback = Callable[[PolyTick], Awaitable[None]]


class PolymarketStreamClient:
    """WebSocket client for real-time Polymarket CLOB orderbook ticks.

    Automatically reconnects with exponential backoff on disconnect.
    Uses the `book` channel for precise bid/ask data rather than
    mid-price approximations.
    """

    def __init__(self) -> None:
        self._token_ids: set[str] = set()
        self._callbacks: list[PolyTickCallback] = []
        self._cache: dict[str, PolyTick] = {}
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._running = False

    # ── Public API ─────────────────────────────────────────────────────────

    def subscribe(self, token_ids: list[str]) -> None:
        """Add token IDs to the subscription set."""
        self._token_ids.update(token_ids)

    def on_tick(self, callback: PolyTickCallback) -> None:
        """Register a coroutine called on every book update."""
        self._callbacks.append(callback)

    def latest(self, token_id: str) -> PolyTick | None:
        """Return the most recent tick for a token, or None."""
        return self._cache.get(token_id)

    async def run(self) -> None:
        """Connect and stream indefinitely; reconnects on error."""
        self._running = True
        backoff = 1.0
        while self._running:
            try:
                await self._connect_and_stream()
                backoff = 1.0
            except websockets.exceptions.ConnectionClosed as exc:
                logger.warning("Polymarket WS closed (%s) — retry in %.0fs", exc, backoff)
            except Exception as exc:
                logger.error("Polymarket WS error: %s — retry in %.0fs", exc, backoff)
            if self._running:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    # ── Internal ───────────────────────────────────────────────────────────

    async def _connect_and_stream(self) -> None:
        async with websockets.connect(
            _WS_URL,
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            self._ws = ws
            logger.info(
                "Polymarket WS connected — subscribing %d tokens", len(self._token_ids)
            )
            if self._token_ids:
                await self._send_subscribe(ws)
            async for raw in ws:
                await self._dispatch(raw)

    async def _send_subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        # Subscribe to market channel — channel is specified in the WS URL path
        await ws.send(json.dumps({
            "type": "subscribe",
            "assets_ids": list(self._token_ids),
        }))

    async def _dispatch(self, raw: str | bytes) -> None:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        # Messages arrive as a single object or a list of objects
        events = data if isinstance(data, list) else [data]

        for event in events:
            event_type = event.get("event_type") or event.get("type", "")

            if event_type == "book":
                await self._handle_book(event)
            elif event_type == "price_change":
                await self._handle_price_change(event)

    async def _handle_book(self, event: dict) -> None:
        token_id = event.get("asset_id", "")
        if not token_id:
            return

        bids: list[dict] = event.get("bids", [])
        asks: list[dict] = event.get("asks", [])

        best_bid = _best_bid(bids)
        best_ask = _best_ask(asks)
        if best_ask <= 0:
            return  # no liquidity on ask side, skip

        tick = PolyTick(
            token_id=token_id,
            best_bid=best_bid,
            best_ask=best_ask,
            mid=(best_bid + best_ask) / 2 if best_bid > 0 else best_ask,
        )
        await self._emit(tick)

    async def _handle_price_change(self, event: dict) -> None:
        """Fallback for price_change events (mid-price only, no spread)."""
        token_id = event.get("asset_id", "")
        price_str = event.get("price", "")
        if not token_id or not price_str:
            return

        try:
            price = float(price_str)
        except ValueError:
            return

        # Use cached spread if available, otherwise assume price is mid
        cached = self._cache.get(token_id)
        if cached:
            half_spread = (cached.best_ask - cached.best_bid) / 2
            tick = PolyTick(
                token_id=token_id,
                best_bid=price - half_spread,
                best_ask=price + half_spread,
                mid=price,
            )
        else:
            # No book data yet — treat price as ask (conservative for arb)
            tick = PolyTick(
                token_id=token_id,
                best_bid=price,
                best_ask=price,
                mid=price,
            )

        await self._emit(tick)

    async def _emit(self, tick: PolyTick) -> None:
        self._cache[tick.token_id] = tick
        for cb in self._callbacks:
            try:
                await cb(tick)
            except Exception as exc:
                logger.error("Polymarket tick callback error: %s", exc)


# ── Helpers ────────────────────────────────────────────────────────────────

def _best_bid(levels: list[dict]) -> float:
    """Highest bid price from an orderbook level list."""
    best = 0.0
    for level in levels:
        try:
            p = float(level.get("price", 0))
            if p > best:
                best = p
        except (TypeError, ValueError):
            pass
    return best


def _best_ask(levels: list[dict]) -> float:
    """Lowest ask price from an orderbook level list."""
    best = 1.0
    found = False
    for level in levels:
        try:
            p = float(level.get("price", 0))
            if p > 0 and (not found or p < best):
                best = p
                found = True
        except (TypeError, ValueError):
            pass
    return best if found else 0.0
