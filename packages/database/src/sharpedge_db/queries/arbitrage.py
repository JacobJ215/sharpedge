"""Database queries for arbitrage opportunities."""

from datetime import datetime, timezone, timedelta
from typing import Any

from sharpedge_db.client import get_supabase_client


def store_arbitrage(
    game_id: str,
    game: str,
    sport: str,
    bet_type: str,
    book_a: str,
    side_a: str,
    odds_a: int,
    stake_a_percentage: float,
    book_b: str,
    side_b: str,
    odds_b: int,
    stake_b_percentage: float,
    profit_percentage: float,
    total_implied: float,
) -> dict | None:
    """Store an arbitrage opportunity.

    Args:
        game_id: Game identifier
        game: Game description
        sport: Sport code
        bet_type: 'spread', 'total', 'moneyline'
        book_a: First sportsbook
        side_a: Selection at book A
        odds_a: Odds at book A
        stake_a_percentage: % of stake for book A
        book_b: Second sportsbook
        side_b: Selection at book B
        odds_b: Odds at book B
        stake_b_percentage: % of stake for book B
        profit_percentage: Guaranteed profit %
        total_implied: Combined implied probability

    Returns:
        Created record or None
    """
    client = get_supabase_client()

    try:
        result = client.table("arbitrage_opportunities").insert({
            "game_id": game_id,
            "game": game,
            "sport": sport,
            "bet_type": bet_type,
            "book_a": book_a,
            "side_a": side_a,
            "odds_a": odds_a,
            "stake_a_percentage": stake_a_percentage,
            "book_b": book_b,
            "side_b": side_b,
            "odds_b": odds_b,
            "stake_b_percentage": stake_b_percentage,
            "profit_percentage": profit_percentage,
            "total_implied": total_implied,
            "is_active": True,
        }).execute()

        return result.data[0] if result.data else None
    except Exception:
        return None


def get_active_arbitrage(
    min_profit: float = 0.5,
    sport: str | None = None,
) -> list[dict]:
    """Get active arbitrage opportunities.

    Args:
        min_profit: Minimum profit percentage
        sport: Filter by sport

    Returns:
        List of active arb opportunities
    """
    client = get_supabase_client()

    query = (
        client.table("arbitrage_opportunities")
        .select("*")
        .eq("is_active", True)
        .gte("profit_percentage", min_profit)
        .order("profit_percentage", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.limit(20).execute()

    return result.data or []


def expire_arbitrage(arb_id: str) -> bool:
    """Mark an arbitrage opportunity as expired.

    Args:
        arb_id: Arbitrage UUID

    Returns:
        True if updated
    """
    client = get_supabase_client()

    try:
        client.table("arbitrage_opportunities").update({
            "is_active": False,
            "expired_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", arb_id).execute()
        return True
    except Exception:
        return False


def expire_old_arbitrage(max_age_minutes: int = 60) -> int:
    """Expire old arbitrage opportunities.

    Args:
        max_age_minutes: Max age before expiring

    Returns:
        Number of arbs expired
    """
    client = get_supabase_client()

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).isoformat()

    result = (
        client.table("arbitrage_opportunities")
        .update({
            "is_active": False,
            "expired_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("is_active", True)
        .lt("detected_at", cutoff)
        .execute()
    )

    return len(result.data) if result.data else 0


def get_arbitrage_stats(days: int = 30) -> dict:
    """Get arbitrage statistics.

    Args:
        days: Look back this many days

    Returns:
        Stats on arb opportunities found
    """
    client = get_supabase_client()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    result = (
        client.table("arbitrage_opportunities")
        .select("profit_percentage, sport, bet_type")
        .gte("detected_at", cutoff)
        .execute()
    )

    arbs = result.data or []
    if not arbs:
        return {
            "total_found": 0,
            "avg_profit": 0,
            "max_profit": 0,
            "by_sport": {},
            "by_bet_type": {},
        }

    by_sport: dict[str, int] = {}
    by_bet_type: dict[str, int] = {}

    for arb in arbs:
        sport = arb.get("sport", "Unknown")
        bet_type = arb.get("bet_type", "Unknown")
        by_sport[sport] = by_sport.get(sport, 0) + 1
        by_bet_type[bet_type] = by_bet_type.get(bet_type, 0) + 1

    profits = [a["profit_percentage"] for a in arbs if a.get("profit_percentage")]

    return {
        "total_found": len(arbs),
        "avg_profit": round(sum(profits) / len(profits), 2) if profits else 0,
        "max_profit": round(max(profits), 2) if profits else 0,
        "by_sport": by_sport,
        "by_bet_type": by_bet_type,
    }
