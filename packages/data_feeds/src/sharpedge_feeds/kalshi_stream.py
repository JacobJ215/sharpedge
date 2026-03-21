"""Real-time WebSocket client for Kalshi market data.

Subscribes to the `ticker` channel which pushes best bid/ask updates
as they occur — enabling sub-second arb detection vs. the 2-minute
polling loop.

Kalshi WS API v2:
  wss://api.elections.kalshi.com/trade-api/ws/v2
  Auth: same RSA-PSS headers passed as HTTP upgrade headers
  Subscribe cmd: {"id": N, "cmd": "subscribe", "params": {"channels": ["ticker"], "market_tickers": [...]}}
  Tick msg type: "ticker"
"""

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import websockets
import websockets.exceptions

from .kalshi_client import KalshiConfig, _rsa_pss_sign

logger = logging.getLogger(__name__)

_WS_PATH = "/trade-api/ws/v2"


def _ws_base(config: KalshiConfig) -> str:
    return config.base_url.replace("https://", "wss://")


@dataclass
class KalshiTick:
    """Real-time price tick from Kalshi ticker channel."""

    ticker: str
    yes_bid: float  # 0-1
    yes_ask: float  # 0-1
    no_bid: float  # 0-1
    no_ask: float  # 0-1
    timestamp: float = field(default_factory=time.time)


TickCallback = Callable[[KalshiTick], Awaitable[None]]


class KalshiStreamClient:
    """WebSocket client for real-time Kalshi bid/ask ticks.

    Reconnects automatically on disconnect with exponential backoff.
    Call `subscribe()` to register tickers before or during a run.
    """

    def __init__(self, config: KalshiConfig) -> None:
        self._config = config
        self._tickers: set[str] = set()
        self._callbacks: list[TickCallback] = []
        self._cache: dict[str, KalshiTick] = {}
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._running = False
        self._msg_id = 0

    # ── Public API ─────────────────────────────────────────────────────────

    def subscribe(self, tickers: list[str]) -> None:
        """Add tickers to the subscription set (effective on next connect)."""
        self._tickers.update(tickers)

    def on_tick(self, callback: TickCallback) -> None:
        """Register a coroutine called on every price update."""
        self._callbacks.append(callback)

    def latest(self, ticker: str) -> KalshiTick | None:
        """Return the most recent tick for a ticker, or None."""
        return self._cache.get(ticker)

    async def run(self) -> None:
        """Connect and stream indefinitely; reconnects on error."""
        self._running = True
        backoff = 1.0
        while self._running:
            try:
                await self._connect_and_stream()
                backoff = 1.0
            except websockets.exceptions.ConnectionClosed as exc:
                logger.warning("Kalshi WS closed (%s) — retry in %.0fs", exc, backoff)
            except Exception as exc:
                logger.error("Kalshi WS error: %s — retry in %.0fs", exc, backoff)
            if self._running:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()

    # ── Internal ───────────────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        ts = str(int(time.time() * 1000))
        headers: dict[str, str] = {
            "KALSHI-ACCESS-KEY": self._config.api_key,
            "KALSHI-ACCESS-TIMESTAMP": ts,
        }
        if self._config.private_key_pem:
            msg = f"{ts}GET{_WS_PATH}"
            headers["KALSHI-ACCESS-SIGNATURE"] = _rsa_pss_sign(self._config.private_key_pem, msg)
        return headers

    async def _connect_and_stream(self) -> None:
        url = f"{_ws_base(self._config)}{_WS_PATH}"
        async with websockets.connect(
            url,
            additional_headers=self._auth_headers(),
            ping_interval=20,
            ping_timeout=10,
        ) as ws:
            self._ws = ws
            logger.info("Kalshi WS connected — subscribing %d tickers", len(self._tickers))
            if self._tickers:
                await self._send_subscribe(ws)
            async for raw in ws:
                await self._dispatch(raw)

    async def _send_subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        self._msg_id += 1
        await ws.send(
            json.dumps(
                {
                    "id": self._msg_id,
                    "cmd": "subscribe",
                    "params": {
                        "channels": ["ticker"],
                        "market_tickers": list(self._tickers),
                    },
                }
            )
        )

    async def _dispatch(self, raw: str | bytes) -> None:
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return

        if data.get("type") != "ticker":
            return

        msg = data.get("msg", {})
        ticker = msg.get("market_ticker") or msg.get("ticker", "")
        if not ticker:
            return

        tick = KalshiTick(
            ticker=ticker,
            yes_bid=int(msg.get("yes_bid", 0)) / 100,
            yes_ask=int(msg.get("yes_ask", 0)) / 100,
            no_bid=int(msg.get("no_bid", 0)) / 100,
            no_ask=int(msg.get("no_ask", 0)) / 100,
        )
        self._cache[ticker] = tick

        for cb in self._callbacks:
            try:
                await cb(tick)
            except Exception as exc:
                logger.error("Kalshi tick callback error: %s", exc)
