"""Kalshi Executor — places real orders via Kalshi REST API."""
from __future__ import annotations

import logging
import os
import uuid

from sharpedge_trading.events.types import ExecutionEvent
from sharpedge_trading.execution.base_executor import BaseExecutor

logger = logging.getLogger(__name__)


def _idempotency_key(event: ExecutionEvent) -> str:
    return f"{event.market_id}:{event.direction}:{event.created_at.isoformat()}"


class KalshiExecutor(BaseExecutor):
    """Places real orders via Kalshi REST API. Activated by TRADING_MODE=live."""

    def __init__(self, supabase_url: str = "", supabase_key: str = "") -> None:
        self._supabase_url = supabase_url or os.environ.get("SUPABASE_URL", "")
        self._supabase_key = supabase_key or os.environ.get("SUPABASE_SERVICE_KEY", "")
        self._filled: set[str] = set()

    async def execute(self, event: ExecutionEvent) -> str | None:
        """Place a live order via Kalshi API. Returns trade_id or None on failure."""
        key = _idempotency_key(event)
        if key in self._filled:
            logger.warning("Duplicate order suppressed for %s (key=%s)", event.market_id, key)
            return None

        # Durable idempotency: check Supabase before placing live order
        if await self._already_filled(key):
            logger.warning("Durable duplicate fill suppressed for %s", event.market_id)
            return None

        trade_id = str(uuid.uuid4())

        try:
            result = await self._place_order(event, trade_id)
            if result:
                self._filled.add(key)
                await self._write_trade(event, trade_id, key)
                return trade_id
            return None
        except Exception as exc:  # noqa: BLE001
            logger.error("Kalshi order failed for %s: %s", event.market_id, exc)
            return None

    async def _already_filled(self, key: str) -> bool:
        """Check Supabase live_trades for existing fill with this idempotency key."""
        if not self._supabase_url or not self._supabase_key:
            return False
        try:
            import asyncio
            from supabase import create_client  # type: ignore[import]
            loop = asyncio.get_running_loop()
            client = create_client(self._supabase_url, self._supabase_key)
            result = await loop.run_in_executor(
                None,
                lambda: client.table("live_trades").select("id").eq("idempotency_key", key).limit(1).execute(),
            )
            return bool(result.data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Durable idempotency check failed: %s — using in-memory guard only", exc)
            return False

    async def _place_order(self, event: ExecutionEvent, trade_id: str) -> bool:
        """Place order via Kalshi client.create_order (async). Returns True on success.

        KalshiClient.create_order signature:
            create_order(ticker, action, side, order_type, count,
                         yes_price=None, no_price=None, expiration_ts=None)

        - count: number of contracts (Kalshi uses integer contract counts)
        - yes_price / no_price: price in cents (1-99)
        - We send a market order so no explicit price is required.
        """
        try:
            from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig  # type: ignore[import]

            api_key = os.environ.get("KALSHI_API_KEY", "")
            private_key_pem = os.environ.get("KALSHI_PRIVATE_KEY_PEM") or None
            demo = os.environ.get("KALSHI_ENV", "prod") == "demo"

            config = KalshiConfig(
                api_key=api_key,
                private_key_pem=private_key_pem,
                environment="demo" if demo else "prod",
            )
            client = KalshiClient(config)

            try:
                count = max(1, int(event.size))  # Kalshi counts are integer contracts
                # Use a limit order priced at entry_price (converted to cents)
                yes_price_cents = int(round(event.entry_price * 100))
                yes_price_cents = max(1, min(99, yes_price_cents))

                order = await client.create_order(
                    ticker=event.market_id,
                    action="buy",
                    side=event.direction,
                    order_type="limit",
                    count=count,
                    yes_price=yes_price_cents if event.direction == "yes" else None,
                    no_price=yes_price_cents if event.direction == "no" else None,
                )
                logger.info(
                    "Kalshi order placed: %s %s $%.2f @ %.4f (order_id=%s)",
                    event.market_id, event.direction, event.size, event.entry_price,
                    order.order_id,
                )
                return True
            finally:
                await client.close()
        except Exception as exc:  # noqa: BLE001
            logger.error("Kalshi API call failed: %s", exc)
            return False

    async def _write_trade(self, event: ExecutionEvent, trade_id: str, key: str) -> None:
        if not self._supabase_url or not self._supabase_key:
            return
        try:
            import asyncio
            from supabase import create_client  # type: ignore[import]
            trade = {
                "id": trade_id,
                "market_id": event.market_id,
                "direction": event.direction,
                "size": event.size,
                "entry_price": event.entry_price,
                "trading_mode": "live",
                "idempotency_key": key,
            }
            loop = asyncio.get_running_loop()
            client = create_client(self._supabase_url, self._supabase_key)
            await loop.run_in_executor(
                None,
                lambda: client.table("live_trades").upsert(trade, on_conflict="id").execute(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write live trade to Supabase: %s", exc)
