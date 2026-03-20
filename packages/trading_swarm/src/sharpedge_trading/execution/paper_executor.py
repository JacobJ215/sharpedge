"""Paper Executor — simulates fills against a virtual bankroll."""
from __future__ import annotations

import logging
import os
import uuid

from sharpedge_trading.events.types import ExecutionEvent
from sharpedge_trading.execution.base_executor import BaseExecutor

logger = logging.getLogger(__name__)

_MARKET_IMPACT_FACTOR = 0.001  # slippage: (size / volume) × 0.001


def _compute_slippage(size: float, entry_price: float, market_volume: float) -> float:
    """Slippage model: spread/2 + (size / volume) × 0.001"""
    spread = 0.02  # assumed 2% spread if no order book data
    market_impact = (size / max(market_volume, 1.0)) * _MARKET_IMPACT_FACTOR
    return spread / 2 + market_impact


def _get_supabase_client(url: str, key: str):  # type: ignore[return]
    """Return a Supabase client. Separated for easy patching in tests."""
    from supabase import create_client  # type: ignore[import]
    return create_client(url, key)


def _idempotency_key(event: ExecutionEvent) -> str:
    """Unique key: market_id + direction + created_at timestamp."""
    return f"{event.market_id}:{event.direction}:{event.created_at.isoformat()}"


class PaperExecutor(BaseExecutor):
    """Simulates fills at current Kalshi mid-price with slippage model."""

    def __init__(self, supabase_url: str = "", supabase_key: str = "") -> None:
        self._supabase_url = supabase_url or os.environ.get("SUPABASE_URL", "")
        self._supabase_key = supabase_key or os.environ.get("SUPABASE_SERVICE_KEY", "")
        self._filled: set[str] = set()  # in-memory idempotency guard
        self._bankroll: float = float(os.environ.get("PAPER_BANKROLL", "10000"))

    async def execute(self, event: ExecutionEvent) -> str | None:
        """Simulate a paper fill. Returns trade_id or None on failure."""
        key = _idempotency_key(event)
        if key in self._filled:
            logger.warning("Duplicate fill suppressed for %s (key=%s)", event.market_id, key)
            return None

        # Compute fill price with slippage
        market_volume = event.size * 20  # estimate: assume our size is ~5% of market
        slippage = _compute_slippage(event.size, event.entry_price, market_volume)
        fill_price = event.entry_price + slippage if event.direction == "yes" else event.entry_price - slippage
        fill_price = max(0.01, min(0.99, fill_price))

        cost = fill_price * event.size
        if cost > self._bankroll:
            logger.warning(
                "Insufficient paper bankroll for %s: cost=%.2f > balance=%.2f",
                event.market_id, cost, self._bankroll,
            )
            return None
        self._bankroll -= cost

        trade_id = str(uuid.uuid4())
        self._filled.add(key)

        trade = {
            "id": trade_id,
            "market_id": event.market_id,
            "direction": event.direction,
            "size": event.size,
            "entry_price": fill_price,
            "trading_mode": "paper",
        }

        await self._write_trade(trade)
        logger.info(
            "Paper fill: %s %s $%.2f @ %.4f (slippage=%.4f, bankroll=%.2f)",
            event.market_id, event.direction, event.size, fill_price, slippage, self._bankroll,
        )
        return trade_id

    async def _write_trade(self, trade: dict) -> None:
        """Write trade to Supabase paper_trades table."""
        if not self._supabase_url or not self._supabase_key:
            logger.debug("No Supabase credentials — trade not persisted: %s", trade["id"])
            return
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            client = _get_supabase_client(self._supabase_url, self._supabase_key)
            await loop.run_in_executor(
                None,
                lambda: client.table("paper_trades").upsert(trade, on_conflict="id").execute(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to write paper trade to Supabase: %s", exc)
