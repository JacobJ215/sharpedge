"""GET /api/v1/games/{game_id}/analysis — full game analysis state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sharpedge_db.queries.injuries import get_injuries_for_game_label
from sharpedge_db.queries.value_plays import get_active_value_plays

router = APIRouter(tags=["v1"])


def load_injuries_for_analysis(match: dict) -> list[dict]:
    """Resolve injuries for a value-play row (patch target for tests)."""
    return get_injuries_for_game_label(
        str(match.get("game") or ""),
        str(match.get("sport") or ""),
    )


@router.get("/games/{game_id}/analysis")
async def game_analysis(game_id: str) -> dict:
    """Return full analysis state for a game. Public endpoint — no auth required."""
    rows = get_active_value_plays(limit=200)
    match = next((r for r in rows if str(r.get("id", "")) == game_id), None)

    if match is None:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

    return {
        "game_id": game_id,
        "model_prediction": {
            "win_probability": float(match.get("win_prob") or 0.0),
            "confidence": match.get("confidence") or "MEDIUM",
        },
        "ev_breakdown": {
            "ev_percentage": float(match.get("ev_percentage") or 0.0),
            "fair_odds": float(match.get("fair_odds") or 0.0),
            "market_odds": float(match.get("market_odds") or 0.0),
        },
        "regime_state": match.get("regime_state") or "UNKNOWN",
        "key_number_proximity": match.get("key_number_proximity") or None,
        "alpha_score": float(match.get("alpha_score") or 0.0),
        "alpha_badge": match.get("alpha_badge") or "SPECULATIVE",
        "injuries": load_injuries_for_analysis(match),
    }
