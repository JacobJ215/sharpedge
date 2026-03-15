"""GET /api/v1/prediction-markets/correlation and GET /api/v1/line-movement endpoints.

Both are public endpoints (no auth required) that source data from the PM correlation
scanner and odds monitor jobs. Graceful degradation — any import or runtime error returns
an empty list rather than a 500.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(tags=["v1"])


def _fetch_pm_correlation(sport: str | None) -> list[dict]:
    """Lazy import of PM correlation scanner; returns empty list on any failure."""
    try:
        from sharpedge_bot.jobs.pm_correlation import get_pm_correlation_data  # type: ignore[import]
        results = get_pm_correlation_data(sport=sport)
        return list(results) if results else []
    except Exception:
        pass

    # Second fallback: try prediction_market_scanner module
    try:
        from sharpedge_bot.jobs.prediction_market_scanner import scan_pm_edges  # type: ignore[import]
        results = scan_pm_edges()
        items = []
        for r in (results or []):
            if hasattr(r, "__dict__"):
                items.append(r.__dict__)
            elif isinstance(r, dict):
                items.append(r)
        return items
    except Exception:
        return []


def _fetch_line_movement() -> list[dict]:
    """Lazy import of odds monitor / opening lines scanner; returns empty list on failure."""
    try:
        from sharpedge_bot.jobs.odds_monitor import get_line_movements  # type: ignore[import]
        results = get_line_movements()
        return list(results) if results else []
    except Exception:
        pass

    try:
        from sharpedge_bot.jobs.opening_lines import get_opening_line_movements  # type: ignore[import]
        results = get_opening_line_movements()
        return list(results) if results else []
    except Exception:
        return []


@router.get("/prediction-markets/correlation")
async def pm_correlation(
    sport: str | None = Query(None, description="Filter by sport (e.g. nfl, nba)"),
) -> list[dict]:
    """Return PM correlation data.

    Sources from the PM correlation scanner. Returns an empty list when the scanner
    is unavailable — no 500, no crash. Public endpoint — no auth required.
    """
    try:
        return _fetch_pm_correlation(sport=sport)
    except Exception:
        return []


@router.get("/line-movement")
async def line_movement() -> list[dict]:
    """Return line movement data from the live odds scanner.

    Returns an empty list when the scanner is unavailable. Public endpoint — no auth required.
    """
    try:
        return _fetch_line_movement()
    except Exception:
        return []
