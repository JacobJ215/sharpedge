"""Copilot tools: Phase 6 venue infrastructure tools.

Two tools exposing cross-venue dislocation and exposure book state.
Kept in a separate file because tools.py is at 447 lines (500-line limit).

Import boundary: packages/* only. Do NOT import from apps/bot (circular dep).
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger("sharpedge.copilot.venue_tools")

# ---------------------------------------------------------------------------
# Module-level ExposureBook singleton (persists across copilot turns)
# ---------------------------------------------------------------------------

_EXPOSURE_BOOK: Any = None


def _get_exposure_book() -> Any:
    global _EXPOSURE_BOOK
    if _EXPOSURE_BOOK is None:
        try:
            from sharpedge_venue_adapters.exposure import ExposureBook
            bankroll = float(os.environ.get("SHARPEDGE_BANKROLL", "10000.0"))
            _EXPOSURE_BOOK = ExposureBook(bankroll=bankroll)
        except ImportError:
            return None
    return _EXPOSURE_BOOK


def _run_async(coro) -> Any:
    """Run an async coroutine from sync context (bridges to event loop)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in event loop (e.g. FastAPI) — use run_in_executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tool 11: get_venue_dislocation
# ---------------------------------------------------------------------------

@tool
def get_venue_dislocation(market_id: str, venue_ids: str = "kalshi,polymarket") -> dict:
    """Get cross-venue dislocation scores for a specific market.

    Compares mid prices across venues (Kalshi, Polymarket). A high dislocation
    score (in basis points) suggests a pricing inefficiency between venues.
    Stale quotes are flagged.

    Args:
        market_id: The market identifier to check (e.g. "KXBTCD-26MAR14")
        venue_ids: Comma-separated venue names to compare. Default: "kalshi,polymarket"

    Returns:
        dict with consensus_prob, per-venue dislocation scores, and stale flags.
    """
    try:
        from sharpedge_venue_adapters.dislocation import score_dislocation
        from sharpedge_venue_adapters.protocol import CanonicalQuote

        venues = [v.strip() for v in venue_ids.split(",")]
        quotes: list[CanonicalQuote] = []

        for venue in venues:
            try:
                if venue == "kalshi":
                    from sharpedge_venue_adapters.adapters.kalshi import KalshiAdapter
                    adapter = KalshiAdapter(api_key=os.environ.get("KALSHI_API_KEY"))
                    market = _run_async(adapter.get_market_details(market_id))
                    fee_schedule = _run_async(adapter.get_fees_and_limits())
                elif venue == "polymarket":
                    from sharpedge_venue_adapters.adapters.polymarket import PolymarketAdapter
                    adapter = PolymarketAdapter()
                    market = _run_async(adapter.get_market_details(market_id))
                    fee_schedule = _run_async(adapter.get_fees_and_limits())
                else:
                    continue

                if market is None:
                    continue

                mid = (market.yes_bid + market.yes_ask) / 2.0
                spread = max(0.0, market.yes_ask - market.yes_bid)
                quote = CanonicalQuote(
                    venue_id=venue,
                    market_id=market_id,
                    outcome_id="yes",
                    raw_bid=market.yes_bid,
                    raw_ask=market.yes_ask,
                    raw_format="probability",
                    fair_prob=mid,
                    mid_prob=mid,
                    spread_prob=spread,
                    maker_fee_rate=fee_schedule.maker_fee_rate,
                    taker_fee_rate=fee_schedule.taker_fee_rate,
                    timestamp_utc=datetime.now(timezone.utc).isoformat(),
                )
                quotes.append(quote)
            except Exception as e:
                logger.debug("Venue %s unavailable for market %s: %s", venue, market_id, e)

        if not quotes:
            return {"error": "No quotes available", "market_id": market_id, "venues_tried": venues}

        scores = score_dislocation(quotes)
        return {
            "market_id": market_id,
            "consensus_prob": round(scores[0].consensus_prob, 4) if scores else None,
            "scores": [
                {
                    "venue_id": s.venue_id,
                    "mid_prob": round(s.venue_mid_prob, 4),
                    "disloc_bps": round(s.disloc_bps, 1),
                    "is_stale": s.is_stale,
                }
                for s in scores[:10]
            ],
        }

    except Exception as e:
        return {"error": str(e), "market_id": market_id}


# ---------------------------------------------------------------------------
# Tool 12: get_exposure_status
# ---------------------------------------------------------------------------

@tool
def get_exposure_status(venue_id: str = "") -> dict:
    """Get the current exposure book state — how much is staked across venues.

    Shows total exposure and per-venue breakdown. Use this when the user asks
    about their current position concentration or venue risk.

    Args:
        venue_id: Optional venue to filter by (e.g. "kalshi"). Empty = all venues.

    Returns:
        dict with total_exposure and per-venue breakdown with utilization %.
    """
    try:
        book = _get_exposure_book()
        if book is None:
            return {"error": "venue_adapters package not available", "venue_id": venue_id}

        known_venues = ["kalshi", "polymarket", "odds_api"]
        venue_breakdown = []
        for v in known_venues:
            if venue_id and v != venue_id:
                continue
            exposure = book.venue_exposure(v)
            utilization = book.venue_utilization(v)
            venue_breakdown.append({
                "venue_id": v,
                "exposure": round(exposure, 2),
                "utilization_pct": round(utilization * 100, 1),
                "cap_pct": round(book.venue_concentration_cap * 100, 1),
                "cap_headroom_pct": round(
                    max(0.0, book.venue_concentration_cap - utilization) * 100, 1
                ),
            })

        return {
            "total_exposure": round(book.total_exposure(), 2),
            "bankroll": round(book.bankroll, 2),
            "venue_concentration_cap_pct": round(book.venue_concentration_cap * 100, 1),
            "venues": venue_breakdown,
        }

    except Exception as e:
        return {"error": str(e), "venue_id": venue_id}


# ---------------------------------------------------------------------------
# Exported tool list
# ---------------------------------------------------------------------------

VENUE_TOOLS = [
    get_venue_dislocation,
    get_exposure_status,
]
