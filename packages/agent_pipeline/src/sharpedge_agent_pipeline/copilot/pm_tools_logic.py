"""Copilot prediction-market helpers: bounded market fetch + analytics (no orders)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from sharpedge_analytics.pm_correlation import (
    compute_entity_correlation,
    detect_correlated_positions,
)
from sharpedge_analytics.pm_edge_scanner import PMEdge, scan_pm_edges
from sharpedge_db.queries.bets import get_pending_bets


def _serialize_edge(e: PMEdge) -> dict[str, Any]:
    return {
        "platform": e.platform,
        "market_id": e.market_id,
        "market_title": e.market_title,
        "edge_pct": e.edge_pct,
        "alpha_badge": e.alpha_badge,
        "regime": e.regime,
        "market_prob": e.market_prob,
        "model_prob": e.model_prob,
    }


async def _scan_top_pm_edges_async(max_markets: int, max_edges: int) -> dict[str, Any]:
    from sharpedge_feeds.kalshi_client import get_kalshi_client
    from sharpedge_feeds.polymarket_client import get_polymarket_client

    half = max(1, max_markets // 2)
    k_markets: list = []
    p_markets: list = []

    kalshi_key = os.environ.get("KALSHI_API_KEY", "")
    kalshi_private_key = os.environ.get("KALSHI_PRIVATE_KEY", "") or None

    if kalshi_key:
        try:
            kalshi = await get_kalshi_client(kalshi_key, private_key_pem=kalshi_private_key)
            try:
                k_markets = await kalshi.get_markets(paginate_all=False, limit=half)
            finally:
                await kalshi.close()
        except Exception:
            k_markets = []

    try:
        poly_key = os.environ.get("POLYMARKET_API_KEY", None)
        poly = await get_polymarket_client(poly_key)
        try:
            p_raw = await poly.get_markets(limit=half)
            p_markets = list(p_raw or [])[:half]
        finally:
            await poly.close()
    except Exception as exc:
        if not k_markets:
            return {"error": str(exc), "edges": [], "count": 0}
        p_markets = []

    if not k_markets and not p_markets:
        return {
            "error": "No markets fetched (check API keys and network).",
            "edges": [],
            "count": 0,
        }

    edges = scan_pm_edges(k_markets, p_markets, {}, volume_floor=0.0)
    flat: list[PMEdge] = [e for e in edges if isinstance(e, PMEdge)]
    flat.sort(key=lambda x: x.alpha_score, reverse=True)
    taken = flat[:max_edges]
    return {
        "edges": [_serialize_edge(e) for e in taken],
        "count": len(taken),
        "sampled": {"kalshi": len(k_markets), "polymarket": len(p_markets)},
    }


def scan_top_pm_edges_impl(*, max_markets: int = 40, max_edges: int = 10) -> dict[str, Any]:
    """Fetch bounded open markets from Kalshi and/or Polymarket; return top PM edges."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    _scan_top_pm_edges_async(max_markets, max_edges),
                )
                return future.result(timeout=90)
        return loop.run_until_complete(_scan_top_pm_edges_async(max_markets, max_edges))
    except Exception as exc:
        return {"error": str(exc), "edges": [], "count": 0}


def check_pm_correlation_impl(
    pm_market_title: str,
    user_id: str,
    max_warnings: int = 5,
) -> dict[str, Any]:
    """Correlate a PM title with the user's pending sportsbook bets (token overlap)."""
    title = (pm_market_title or "").strip()
    if not title:
        return {
            "correlation": None,
            "warnings": [],
            "count": 0,
            "error": "pm_market_title is required.",
        }

    try:
        bets = list(get_pending_bets(user_id or ""))
    except Exception as exc:
        return {"correlation": None, "warnings": [], "count": 0, "error": str(exc)}

    if not bets:
        return {
            "correlation": None,
            "warnings": [],
            "count": 0,
            "note": "No pending sportsbook bets.",
        }

    correlated = detect_correlated_positions(title, bets, threshold=0.6)
    warnings: list[dict[str, Any]] = []
    best: float | None = None
    for bet in correlated:
        if isinstance(bet, dict):
            sel = str(bet.get("selection", "") or "")
            game = str(bet.get("game", "") or "")
        else:
            sel = str(getattr(bet, "selection", "") or "")
            game = str(getattr(bet, "game", "") or "")
        c1 = compute_entity_correlation(title, sel)
        c2 = compute_entity_correlation(title, game)
        mc = max(c1, c2)
        if best is None or mc > best:
            best = mc
        if len(warnings) < max_warnings:
            warnings.append(
                {
                    "correlation": round(mc, 4),
                    "game": game,
                    "selection": sel,
                }
            )

    return {
        "correlation": round(best, 4) if best is not None else None,
        "warnings": warnings,
        "count": len(warnings),
    }
