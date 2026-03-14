"""Mobile API routes for the SharpEdge Flutter app."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query

from sharpedge_db.queries.arbitrage import get_active_arbitrage
from sharpedge_db.queries.bets import get_performance_summary, get_user_bets_history
from sharpedge_db.queries.line_movements import get_recent_steam_moves
from sharpedge_db.queries.value_plays import get_active_value_plays

router = APIRouter(prefix="/api", tags=["mobile"])


@router.get("/value-plays")
async def value_plays(
    sport: str | None = Query(default=None),
    min_ev: float | None = Query(default=None),
    confidence: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
) -> list[dict]:
    """Return active value plays ordered by EV descending."""
    rows = get_active_value_plays(sport=sport, min_ev=min_ev, confidence=confidence, limit=limit)
    return [
        {
            "id": r.get("id", ""),
            "event": r.get("game", ""),
            "market": r.get("bet_type", ""),
            "team": r.get("side", ""),
            "our_odds": float(r.get("fair_odds") or 0),
            "book_odds": float(r.get("market_odds") or 0),
            "expected_value": float(r.get("ev_percentage") or 0) / 100,
            "book": r.get("sportsbook", ""),
            "timestamp": (r.get("created_at") or r.get("game_start_time") or ""),
        }
        for r in rows
    ]


@router.get("/arbitrage")
async def arbitrage(
    min_profit: float = Query(default=0.5),
    sport: str | None = Query(default=None),
) -> list[dict]:
    """Return active arbitrage opportunities ordered by profit descending."""
    rows = get_active_arbitrage(min_profit=min_profit, sport=sport)
    result = []
    for r in rows:
        legs = [
            {
                "book": r.get("book_a", ""),
                "side": r.get("side_a", ""),
                "odds": float(r.get("odds_a") or 0),
                "stake": float(r.get("stake_a_percentage") or 0),
            },
            {
                "book": r.get("book_b", ""),
                "side": r.get("side_b", ""),
                "odds": float(r.get("odds_b") or 0),
                "stake": float(r.get("stake_b_percentage") or 0),
            },
        ]
        result.append(
            {
                "id": r.get("id", ""),
                "event": r.get("game", ""),
                "market": r.get("bet_type", ""),
                "profit_percent": float(r.get("profit_percentage") or 0),
                "legs": legs,
                "timestamp": r.get("detected_at", ""),
            }
        )
    return result


@router.get("/line-movements")
async def line_movements(
    hours: int = Query(default=24, le=168),
    sport: str | None = Query(default=None),
) -> list[dict]:
    """Return significant line movements (steam + RLM) from the last N hours."""
    rows = get_recent_steam_moves(hours=hours, sport=sport)
    result = []
    for r in rows:
        old_line = float(r.get("old_line") or 0)
        new_line = float(r.get("new_line") or 0)
        movement = float(r.get("magnitude") or abs(new_line - old_line))
        direction = r.get("direction") or ("up" if new_line > old_line else "down")
        result.append(
            {
                "id": r.get("id", ""),
                "event": (
                    r.get("interpretation")
                    or "{sport} game".format(sport=r.get("sport", "").upper()).strip()
                    or r.get("game_id", "")
                ),
                "market": r.get("bet_type", ""),
                "open_line": old_line,
                "current_line": new_line,
                "movement": movement,
                "direction": direction,
                "history": [],
                "timestamp": r.get("detected_at", ""),
            }
        )
    return result


_EMPTY_BANKROLL: dict = {
    "balance": 0.0,
    "starting_balance": 0.0,
    "total_wagered": 0.0,
    "total_returned": 0.0,
    "bets_placed": 0,
    "bets_won": 0,
    "bets_lost": 0,
    "bets_pending": 0,
    "roi": 0.0,
    "win_rate": 0.0,
    "history": [],
}


@router.get("/bankroll")
async def bankroll(
    user_id: str | None = Query(default=None, description="User UUID from Supabase"),
) -> dict:
    """Return bankroll summary for a user. Returns empty data when user_id is omitted."""
    if not user_id:
        return _EMPTY_BANKROLL
    summary = get_performance_summary(user_id=user_id)
    bet_history = get_user_bets_history(user_id=user_id, limit=200)

    # Derive balance history from settled bets (running cumulative profit)
    running_balance = Decimal("0")
    balance_history: list[dict] = []
    for bet in reversed(bet_history):
        running_balance += Decimal(str(bet.get("profit") or 0))
        balance_history.append(
            {
                "balance": float(running_balance),
                "at": bet.get("settled_at") or bet.get("placed_at") or "",
            }
        )

    total_wagered = sum(float(b.get("stake") or 0) for b in bet_history)
    total_returned = total_wagered + float(summary.roi / 100 * Decimal(str(total_wagered)) if total_wagered else Decimal("0"))
    final_balance = float(running_balance)
    pending_count = sum(1 for b in bet_history if b.get("result") == "pending")

    return {
        "balance": final_balance,
        "starting_balance": 0.0,
        "total_wagered": total_wagered,
        "total_returned": total_returned,
        "bets_placed": summary.total_bets,
        "bets_won": summary.wins,
        "bets_lost": summary.losses,
        "bets_pending": pending_count,
        "roi": float(summary.roi),
        "win_rate": float(summary.win_rate) / 100,
        "history": balance_history,
    }
