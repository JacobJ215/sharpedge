"""GET /api/v1/value-plays — alpha-ranked value plays."""
from __future__ import annotations

from fastapi import APIRouter, Query
from sharpedge_db.queries.value_plays import get_active_value_plays

router = APIRouter(tags=["v1"])

_BADGE_THRESHOLDS = [
    (0.85, "PREMIUM"),
    (0.70, "HIGH"),
    (0.50, "MEDIUM"),
    (0.0,  "SPECULATIVE"),
]


def _alpha_badge(score: float) -> str:
    for threshold, badge in _BADGE_THRESHOLDS:
        if score >= threshold:
            return badge
    return "SPECULATIVE"


@router.get("/value-plays")
async def value_plays_v1(
    sport: str | None = Query(default=None),
    min_ev: float | None = Query(default=None),
    min_alpha: float | None = Query(default=None, description="Filter by minimum alpha score"),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    """Alpha-ranked value plays with regime state and alpha badges."""
    rows = get_active_value_plays(sport=sport, min_ev=min_ev, limit=limit)

    plays = []
    for r in rows:
        # alpha_score and regime_state come from DB column if present, else default
        alpha_score = float(r.get("alpha_score") or 0.0)
        regime_state = r.get("regime_state") or "UNKNOWN"

        if min_alpha is not None and alpha_score < min_alpha:
            continue

        plays.append({
            "id": r.get("id", ""),
            "event": r.get("game", ""),
            "market": r.get("bet_type", ""),
            "team": r.get("side", ""),
            "our_odds": float(r.get("fair_odds") or 0),
            "book_odds": float(r.get("market_odds") or 0),
            "expected_value": float(r.get("ev_percentage") or 0) / 100,
            "book": r.get("sportsbook", ""),
            "timestamp": r.get("created_at") or r.get("game_start_time") or "",
            "alpha_score": alpha_score,
            "alpha_badge": _alpha_badge(alpha_score),
            "regime_state": regime_state,
        })

    # Sort by alpha_score descending (highest alpha first — AGENT-05 pattern)
    plays.sort(key=lambda p: p["alpha_score"], reverse=True)
    return plays
