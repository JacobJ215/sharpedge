"""GET /api/v1/users/{user_id}/portfolio — auth-gated portfolio stats."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status

from sharpedge_db.queries.users import (
    get_internal_user_id_by_supabase_auth,
    get_unit_size_for_user,
)
from sharpedge_webhooks.routes.v1.deps import CurrentUser  # noqa: TC001

router = APIRouter(tags=["v1"])


def _is_pending_result(value: object) -> bool:
    return str(value or "").upper() == "PENDING"


def get_performance_summary(user_id: str):
    """Import-time lazy shim — real import happens at call time."""
    from sharpedge_db.queries.bets import get_performance_summary as _fn

    return _fn(user_id=user_id)


def get_user_bets_history(user_id: str, limit: int = 200):
    """Import-time lazy shim — real import happens at call time."""
    from sharpedge_db.queries.bets import get_user_bets_history as _fn

    return _fn(user_id=user_id, limit=limit)


def load_portfolio_breakdowns(internal_user_id: str) -> dict:
    """Aggregate settled-bet slices for the portfolio API (test patch target)."""
    from sharpedge_db.queries.bets import (
        get_breakdown_by_bet_type,
        get_breakdown_by_juice_bucket,
        get_breakdown_by_sport,
        get_breakdown_by_sportsbook,
    )

    sports = get_breakdown_by_sport(internal_user_id)
    types = get_breakdown_by_bet_type(internal_user_id)
    books = get_breakdown_by_sportsbook(internal_user_id)
    juice = get_breakdown_by_juice_bucket(internal_user_id)
    return {
        "by_sport": [
            {
                "sport": str(s.sport),
                "total_bets": s.total_bets,
                "wins": s.wins,
                "losses": s.losses,
                "win_rate": float(s.win_rate),
                "roi": float(s.roi),
            }
            for s in sports
        ],
        "by_bet_type": [
            {
                "bet_type": str(t.bet_type),
                "total_bets": t.total_bets,
                "wins": t.wins,
                "losses": t.losses,
                "win_rate": float(t.win_rate),
                "roi": float(t.roi),
            }
            for t in types
        ],
        "by_book": books,
        "by_juice": juice,
    }


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

    internal_user_id = get_internal_user_id_by_supabase_auth(user_id)
    if not internal_user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found — complete sign-up or contact support",
        )

    summary = get_performance_summary(user_id=internal_user_id)
    bets = get_user_bets_history(user_id=internal_user_id, limit=500)
    active_bets = [b for b in bets if _is_pending_result(b.get("result"))]
    settled_bets = [b for b in bets if not _is_pending_result(b.get("result"))]

    # CLV average from settled bets with clv field
    clv_values = [float(b["clv"]) for b in bets if b.get("clv") is not None]
    clv_average = sum(clv_values) / len(clv_values) if clv_values else 0.0

    # Running max drawdown
    running_balance = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for bet in reversed(settled_bets):
        running_balance += float(bet.get("profit") or 0)
        if running_balance > peak:
            peak = running_balance
        drawdown = peak - running_balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    # Time-series history: group settled bets by month (oldest first)
    # Bucket key: "YYYY-MM"
    by_month: dict[str, dict] = defaultdict(lambda: {"profit": 0.0, "stake": 0.0})
    for bet in reversed(settled_bets):  # oldest first
        ts = bet.get("settled_at") or bet.get("placed_at") or ""
        if not ts:
            continue
        month_key = ts[:7]  # "YYYY-MM"
        by_month[month_key]["profit"] += float(bet.get("profit") or 0)
        by_month[month_key]["stake"] += float(bet.get("stake") or 0)

    roi_history = []
    bankroll_history = []
    cum_profit = 0.0
    cum_stake = 0.0
    for month_key in sorted(by_month):
        cum_profit += by_month[month_key]["profit"]
        cum_stake += by_month[month_key]["stake"]
        cum_roi = (cum_profit / cum_stake * 100) if cum_stake else 0.0
        # Format label: "Jan '25"
        try:
            from datetime import datetime

            dt = datetime.strptime(month_key, "%Y-%m")
            label = dt.strftime("%b '%y")
        except ValueError:
            label = month_key
        roi_history.append({"date": label, "roi": round(cum_roi, 2)})
        bankroll_history.append({"date": label, "bankroll": round(cum_profit, 2)})

    unit_size = get_unit_size_for_user(internal_user_id)
    breakdowns = load_portfolio_breakdowns(internal_user_id)

    return {
        "user_id": user_id,
        "roi": float(summary.roi),
        "win_rate": float(summary.win_rate) / 100,
        "clv_average": clv_average,
        "drawdown": max_drawdown,
        "unit_size": float(unit_size.quantize(Decimal("0.01"))) if unit_size > 0 else 0.0,
        **breakdowns,
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
        "roi_history": roi_history,
        "bankroll_history": bankroll_history,
    }
