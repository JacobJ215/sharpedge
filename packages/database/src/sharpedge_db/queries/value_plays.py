"""Database queries for value plays."""

from datetime import UTC, datetime

from sharpedge_db.client import get_supabase_client


def store_value_play(
    game_id: str,
    game: str,
    sport: str,
    bet_type: str,
    side: str,
    sportsbook: str,
    market_odds: int,
    model_probability: float,
    implied_probability: float,
    fair_odds: int | None,
    edge_percentage: float,
    ev_percentage: float,
    confidence: str,
    game_start_time: datetime | None = None,
    expires_at: datetime | None = None,
    notes: str = "",
) -> dict | None:
    """Store a detected value play.

    Args:
        game_id: Game identifier
        game: Game description
        sport: Sport code
        bet_type: 'spread', 'total', 'moneyline'
        side: Selection description
        sportsbook: Book offering the value
        market_odds: Current odds
        model_probability: Model's win probability
        implied_probability: Market implied probability
        fair_odds: No-vig fair odds
        edge_percentage: Edge over market
        ev_percentage: Expected value percentage
        confidence: 'HIGH', 'MEDIUM', 'LOW'
        game_start_time: When game starts
        expires_at: When play expires
        notes: Additional notes

    Returns:
        Created record or None
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("value_plays")
            .insert(
                {
                    "game_id": game_id,
                    "game": game,
                    "sport": sport,
                    "bet_type": bet_type,
                    "side": side,
                    "sportsbook": sportsbook,
                    "market_odds": market_odds,
                    "model_probability": model_probability,
                    "implied_probability": implied_probability,
                    "fair_odds": fair_odds,
                    "edge_percentage": edge_percentage,
                    "ev_percentage": ev_percentage,
                    "confidence": confidence,
                    "game_start_time": game_start_time.isoformat() if game_start_time else None,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "is_active": True,
                    "notes": notes,
                }
            )
            .execute()
        )

        return result.data[0] if result.data else None
    except Exception:
        return None


def get_active_value_plays(
    sport: str | None = None,
    min_ev: float | None = None,
    confidence: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Get active value plays where the game has not yet started.

    Filters out plays where game_start_time is in the past — this prevents
    stale/seed rows from appearing after the game has already kicked off.
    Plays with no game_start_time set are always included (PM / futures).

    Args:
        sport: Filter by sport
        min_ev: Minimum EV percentage
        confidence: Filter by confidence level
        limit: Maximum results

    Returns:
        List of active value plays with future game times
    """
    client = get_supabase_client()
    now = datetime.now(UTC).isoformat()

    # Include plays that are either: (a) game hasn't started yet, or (b) no game time set
    query = (
        client.table("value_plays")
        .select("*")
        .eq("is_active", True)
        .or_(f"game_start_time.gt.{now},game_start_time.is.null")
        .order("ev_percentage", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    if min_ev:
        query = query.gte("ev_percentage", min_ev)

    if confidence:
        query = query.eq("confidence", confidence)

    result = query.limit(limit).execute()

    return result.data or []


def get_value_play(play_id: str) -> dict | None:
    """Get a specific value play by ID.

    Args:
        play_id: Value play UUID

    Returns:
        Value play record or None
    """
    client = get_supabase_client()

    result = client.table("value_plays").select("*").eq("id", play_id).limit(1).execute()

    return result.data[0] if result.data else None


def mark_value_play_result(
    play_id: str,
    result: str,
    actual_clv: float | None = None,
) -> bool:
    """Mark a value play with its result.

    Args:
        play_id: Value play UUID
        result: 'win', 'loss', 'push'
        actual_clv: Actual closing line value

    Returns:
        True if updated
    """
    client = get_supabase_client()

    try:
        data = {"result": result, "is_active": False}
        if actual_clv is not None:
            data["actual_clv"] = actual_clv

        client.table("value_plays").update(data).eq("id", play_id).execute()
        return True
    except Exception:
        return False


def expire_old_value_plays() -> int:
    """Expire value plays past their expiration time.

    Returns:
        Number of plays expired
    """
    client = get_supabase_client()

    now = datetime.now(UTC).isoformat()

    result = (
        client.table("value_plays")
        .update({"is_active": False})
        .eq("is_active", True)
        .lt("expires_at", now)
        .execute()
    )

    return len(result.data) if result.data else 0


def get_value_play_stats(sport: str | None = None) -> dict:
    """Get statistics on value play performance.

    Args:
        sport: Filter by sport

    Returns:
        Performance stats
    """
    client = get_supabase_client()

    query = client.table("value_plays").select("result, ev_percentage, confidence")

    if sport:
        query = query.eq("sport", sport)

    result = query.not_.is_("result", "null").execute()

    plays = result.data or []
    if not plays:
        return {
            "total": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "win_rate": 0,
        }

    wins = sum(1 for p in plays if p["result"] == "win")
    losses = sum(1 for p in plays if p["result"] == "loss")
    pushes = sum(1 for p in plays if p["result"] == "push")
    total = wins + losses

    return {
        "total": len(plays),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "avg_ev": round(sum(p["ev_percentage"] for p in plays) / len(plays), 2) if plays else 0,
    }
