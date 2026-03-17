"""Monitor Agent — polls open positions every 60 seconds until settlement."""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import ResolutionEvent

logger = logging.getLogger(__name__)

_POLL_INTERVAL = 60  # seconds


def _get_supabase_client():
    """Create Supabase client from env vars. Returns None if not configured."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore[import]
        return create_client(url, key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to create Supabase client: %s", exc)
        return None


def _fetch_open_positions(client) -> list[dict]:
    """Fetch all open positions from Supabase."""
    try:
        trading_mode = os.environ.get("TRADING_MODE", "paper")
        response = (
            client.table("open_positions")
            .select("id,market_id,size,entry_price,trading_mode")
            .eq("status", "open")
            .eq("trading_mode", trading_mode)
            .execute()
        )
        return response.data or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch open positions: %s", exc)
        return []


async def _check_settlement(market_id: str, kalshi_client) -> tuple[bool, bool]:
    """Check if market has settled. Returns (is_settled, outcome)."""
    try:
        loop = asyncio.get_running_loop()
        market = await loop.run_in_executor(
            None, lambda: kalshi_client.get_market(market_id)
        )
        if isinstance(market, dict):
            status = market.get("status", "")
            result = market.get("result", "")
            if status == "finalized":
                return True, result == "yes"
        return False, False
    except Exception as exc:  # noqa: BLE001
        logger.warning("Settlement check failed for %s: %s", market_id, exc)
        return False, False


def _mark_settled(client, position_id: str) -> None:
    """Mark position as settled in Supabase."""
    try:
        client.table("open_positions").update(
            {"status": "settled", "resolved_at": datetime.now(tz=timezone.utc).isoformat()}
        ).eq("id", position_id).execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to mark position %s as settled: %s", position_id, exc)


async def monitor_once(bus: EventBus, kalshi_client) -> int:
    """Run one monitor cycle. Returns number of settlements emitted."""
    client = _get_supabase_client()
    if client is None:
        logger.debug("No Supabase client — skipping monitor cycle")
        return 0

    positions = _fetch_open_positions(client)
    settled = 0

    for pos in positions:
        market_id = pos.get("market_id", "")
        position_id = pos.get("id", "")
        if not market_id:
            continue

        is_settled, actual_outcome = await _check_settlement(market_id, kalshi_client)
        if not is_settled:
            continue

        # Compute P&L
        size = float(pos.get("size", 0))
        entry_price = float(pos.get("entry_price", 0.5))
        pnl = size * (1.0 - entry_price) if actual_outcome else -size * entry_price

        trading_mode = pos.get("trading_mode", "paper")
        event = ResolutionEvent(
            trade_id=position_id,
            market_id=market_id,
            actual_outcome=actual_outcome,
            pnl=pnl,
            trading_mode=trading_mode,
        )
        await bus.put_resolution(event)
        _mark_settled(client, position_id)
        settled += 1
        logger.info(
            "Settlement: %s | outcome=%s pnl=%.2f",
            market_id, actual_outcome, pnl,
        )

    return settled


async def run_monitor_agent(bus: EventBus, kalshi_client) -> None:
    """Main monitor agent loop — polls every 60 seconds."""
    logger.info("Monitor agent started")
    while True:
        await monitor_once(bus, kalshi_client)
        await asyncio.sleep(_POLL_INTERVAL)
