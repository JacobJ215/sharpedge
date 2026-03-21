"""Database queries for line movements."""

from datetime import UTC, datetime, timedelta

from sharpedge_db.client import get_supabase_client


def store_line_movement(
    game_id: str,
    sport: str,
    bet_type: str,
    old_line: float,
    new_line: float,
    old_odds: int | None = None,
    new_odds: int | None = None,
    sportsbook: str | None = None,
    direction: str | None = None,
    magnitude: float | None = None,
    movement_type: str | None = None,
    confidence: float | None = None,
    interpretation: str | None = None,
    is_significant: bool = False,
    public_side: str | None = None,
) -> dict | None:
    """Store a line movement event.

    Args:
        game_id: Game identifier
        sport: Sport code
        bet_type: 'spread', 'total', 'moneyline'
        old_line: Previous line value
        new_line: New line value
        old_odds: Previous odds
        new_odds: New odds
        sportsbook: Book where movement occurred (None for consensus)
        direction: 'toward_favorite', 'toward_underdog', 'over', 'under'
        magnitude: Size of movement
        movement_type: 'steam', 'rlm', 'gradual', 'buyback', 'correction'
        confidence: Confidence in classification (0-1)
        interpretation: Human-readable explanation
        is_significant: Whether this is a notable movement
        public_side: Which side public was betting when move happened

    Returns:
        Created record or None
    """
    client = get_supabase_client()

    try:
        result = (
            client.table("line_movements")
            .insert(
                {
                    "game_id": game_id,
                    "sport": sport,
                    "bet_type": bet_type,
                    "old_line": old_line,
                    "new_line": new_line,
                    "old_odds": old_odds,
                    "new_odds": new_odds,
                    "sportsbook": sportsbook,
                    "direction": direction,
                    "magnitude": magnitude or abs(new_line - old_line),
                    "movement_type": movement_type,
                    "confidence": confidence,
                    "interpretation": interpretation,
                    "is_significant": is_significant,
                    "public_side": public_side,
                }
            )
            .execute()
        )

        return result.data[0] if result.data else None
    except Exception:
        return None


def get_line_movements(
    game_id: str,
    bet_type: str | None = None,
    significant_only: bool = False,
) -> list[dict]:
    """Get line movements for a game.

    Args:
        game_id: Game identifier
        bet_type: Filter by bet type
        significant_only: Only return significant movements

    Returns:
        List of movements ordered by time
    """
    client = get_supabase_client()

    query = (
        client.table("line_movements")
        .select("*")
        .eq("game_id", game_id)
        .order("detected_at", desc=True)
    )

    if bet_type:
        query = query.eq("bet_type", bet_type)

    if significant_only:
        query = query.eq("is_significant", True)

    result = query.execute()

    return result.data or []


def get_recent_steam_moves(
    hours: int = 24,
    sport: str | None = None,
) -> list[dict]:
    """Get recent steam moves.

    Args:
        hours: Look back this many hours
        sport: Filter by sport

    Returns:
        List of steam moves
    """
    client = get_supabase_client()

    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    query = (
        client.table("line_movements")
        .select("*")
        .eq("movement_type", "steam")
        .gte("detected_at", cutoff)
        .order("detected_at", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.limit(50).execute()

    return result.data or []


def get_reverse_line_movements(
    hours: int = 24,
    sport: str | None = None,
) -> list[dict]:
    """Get reverse line movements (RLM).

    Args:
        hours: Look back this many hours
        sport: Filter by sport

    Returns:
        List of RLM events
    """
    client = get_supabase_client()

    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    query = (
        client.table("line_movements")
        .select("*")
        .eq("movement_type", "rlm")
        .gte("detected_at", cutoff)
        .order("detected_at", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.limit(50).execute()

    return result.data or []


def get_movement_summary(game_id: str) -> dict:
    """Get summary of all movements for a game.

    Args:
        game_id: Game identifier

    Returns:
        Movement summary with total movement, steam moves, etc.
    """
    movements = get_line_movements(game_id)

    if not movements:
        return {
            "game_id": game_id,
            "total_movements": 0,
            "significant_movements": 0,
            "steam_moves": 0,
            "rlm_moves": 0,
            "spread_movement": 0,
            "total_movement": 0,
        }

    spread_movements = [m for m in movements if m["bet_type"] == "spread"]
    total_movements = [m for m in movements if m["bet_type"] == "total"]

    # Calculate net movement
    spread_net = 0
    for m in spread_movements:
        spread_net += (m["new_line"] or 0) - (m["old_line"] or 0)

    total_net = 0
    for m in total_movements:
        total_net += (m["new_line"] or 0) - (m["old_line"] or 0)

    return {
        "game_id": game_id,
        "total_movements": len(movements),
        "significant_movements": sum(1 for m in movements if m.get("is_significant")),
        "steam_moves": sum(1 for m in movements if m.get("movement_type") == "steam"),
        "rlm_moves": sum(1 for m in movements if m.get("movement_type") == "rlm"),
        "spread_net_movement": round(spread_net, 2),
        "total_net_movement": round(total_net, 2),
        "first_movement": movements[-1]["detected_at"] if movements else None,
        "last_movement": movements[0]["detected_at"] if movements else None,
    }


def get_line_history(
    game_id: str,
    bet_type: str = "spread",
    hours: int = 48,
) -> dict:
    """Get line history for chart generation.

    Args:
        game_id: Game identifier
        bet_type: 'spread' or 'total'
        hours: How many hours of history to fetch

    Returns:
        Dict with timestamps, lines, and metadata for charting
    """
    client = get_supabase_client()

    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    result = (
        client.table("line_movements")
        .select("detected_at, new_line, old_line, sportsbook, movement_type, is_significant")
        .eq("game_id", game_id)
        .eq("bet_type", bet_type)
        .gte("detected_at", cutoff)
        .order("detected_at", desc=False)
        .execute()
    )

    movements = result.data or []

    if not movements:
        return {
            "game_id": game_id,
            "bet_type": bet_type,
            "timestamps": [],
            "lines": [],
            "opening_line": None,
            "current_line": None,
            "steam_moves": [],
        }

    # Build time series
    timestamps = []
    lines = []
    steam_timestamps = []

    # Start with first old_line
    opening_line = movements[0].get("old_line") if movements else None

    for m in movements:
        detected_at = m.get("detected_at")
        new_line = m.get("new_line")

        if detected_at and new_line is not None:
            timestamps.append(datetime.fromisoformat(detected_at.replace("Z", "+00:00")))
            lines.append(float(new_line))

            # Track steam moves for highlighting
            if m.get("movement_type") == "steam":
                steam_timestamps.append(detected_at)

    current_line = lines[-1] if lines else None

    return {
        "game_id": game_id,
        "bet_type": bet_type,
        "timestamps": timestamps,
        "lines": lines,
        "opening_line": float(opening_line) if opening_line else None,
        "current_line": current_line,
        "steam_moves": steam_timestamps,
        "total_movements": len(movements),
    }
