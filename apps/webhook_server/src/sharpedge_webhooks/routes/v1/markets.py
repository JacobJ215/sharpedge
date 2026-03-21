"""GET /api/v1/markets/dislocation — cross-venue dislocation scoring (public)."""

from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(tags=["v1"])


def get_venue_dislocation_result(market_id: str, venue_ids: list[str]) -> dict:
    """Lazy wrapper around Phase 6 venue_tools get_venue_dislocation."""
    try:
        from sharpedge_agent_pipeline.copilot.venue_tools import get_venue_dislocation

        result = get_venue_dislocation.invoke(
            {
                "market_id": market_id,
                "venue_ids": ",".join(venue_ids),
            }
        )
        return result
    except Exception:
        return {}


@router.get("/markets/dislocation")
async def markets_dislocation(
    market_id: str = Query(..., description="Market identifier"),
    venue_ids: str | None = Query(None, description="Comma-separated venue IDs"),
) -> dict:
    """Get cross-venue dislocation scores for a market. Public endpoint — no auth required."""
    venue_list: list[str] = (
        [v.strip() for v in venue_ids.split(",")] if venue_ids else ["kalshi", "polymarket"]
    )

    try:
        result = get_venue_dislocation_result(market_id, venue_list)
    except Exception:
        result = {}

    # Graceful degradation — return empty scores on any tool failure
    consensus_prob: float = float(result.get("consensus_prob") or 0.0)
    raw_scores = result.get("scores", [])

    # Build scores dict keyed by venue_id for schema compatibility
    scores_dict: dict[str, dict] = {}
    if isinstance(raw_scores, list):
        for s in raw_scores:
            if isinstance(s, dict) and "venue_id" in s:
                scores_dict[s["venue_id"]] = s

    # Aggregate dislocation_bps across venues (max absolute value)
    dislocation_bps: float = 0.0
    if scores_dict:
        dislocation_bps = max(abs(float(s.get("disloc_bps", 0.0))) for s in scores_dict.values())

    return {
        "market_id": market_id,
        "consensus_prob": consensus_prob,
        "scores": scores_dict,
        "dislocation_bps": round(dislocation_bps, 1),
    }
