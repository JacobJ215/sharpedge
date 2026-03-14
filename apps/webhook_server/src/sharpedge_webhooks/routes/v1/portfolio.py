"""GET /api/v1/users/{user_id}/portfolio — auth-gated portfolio stats."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sharpedge_webhooks.routes.v1.deps import CurrentUser

router = APIRouter(tags=["v1"])


def get_performance_summary(user_id: str):
    """Import-time lazy shim — real import happens at call time."""
    from sharpedge_db.queries.bets import get_performance_summary as _fn
    return _fn(user_id=user_id)


def get_user_bets_history(user_id: str, limit: int = 200):
    """Import-time lazy shim — real import happens at call time."""
    from sharpedge_db.queries.bets import get_user_bets_history as _fn
    return _fn(user_id=user_id, limit=limit)


@router.get("/users/{user_id}/portfolio")
async def portfolio(user_id: str, current_user: CurrentUser) -> dict:
    """Return portfolio stats for a user. Requires valid Supabase JWT.

    RLS ensures Supabase only returns data belonging to the authenticated user.
    We additionally verify the requested user_id matches the JWT user_id.
    """
    if current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot view another user's portfolio",
        )

    summary = get_performance_summary(user_id=user_id)
    bets = get_user_bets_history(user_id=user_id, limit=200)
    active_bets = [b for b in bets if b.get("result") == "pending"]

    # CLV average from settled bets with clv field
    clv_values = [float(b["clv"]) for b in bets if b.get("clv") is not None]
    clv_average = sum(clv_values) / len(clv_values) if clv_values else 0.0

    # Running max drawdown
    running_balance = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for bet in reversed(bets):
        running_balance += float(bet.get("profit") or 0)
        if running_balance > peak:
            peak = running_balance
        drawdown = peak - running_balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return {
        "user_id": user_id,
        "roi": float(summary.roi),
        "win_rate": float(summary.win_rate) / 100,
        "clv_average": clv_average,
        "drawdown": max_drawdown,
        "active_bets": [
            {
                "id": b.get("id", ""),
                "event": b.get("game", ""),
                "stake": float(b.get("stake") or 0),
                "book": b.get("sportsbook", ""),
            }
            for b in active_bets
        ],
        "total_bets": summary.total_bets,
        "wins": summary.wins,
        "losses": summary.losses,
    }
