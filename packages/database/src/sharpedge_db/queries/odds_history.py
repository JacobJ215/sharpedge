from datetime import datetime
from typing import Any

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import OddsHistory


def store_odds_snapshot(
    game_id: str,
    sportsbook: str,
    bet_type: str,
    line: float | None = None,
    odds: int | None = None,
    side: str | None = None,
    game_start_time: datetime | None = None,
) -> OddsHistory:
    """Store an odds snapshot for historical tracking."""
    client = get_supabase_client()
    data: dict = {
        "game_id": game_id,
        "sportsbook": sportsbook,
        "bet_type": bet_type,
    }
    if line is not None:
        data["line"] = line
    if odds is not None:
        data["odds"] = odds
    if side is not None:
        data["side"] = side
    if game_start_time is not None:
        data["game_start_time"] = game_start_time.isoformat()

    result = client.table("odds_history").insert(data).execute()
    return OddsHistory(**result.data[0])


def store_bulk_odds_snapshot(
    snapshots: list[dict[str, Any]],
) -> int:
    """Store multiple odds snapshots efficiently.

    Args:
        snapshots: List of dicts with keys: game_id, sportsbook, bet_type,
                   line (optional), odds (optional), side (optional)

    Returns:
        Number of records inserted
    """
    if not snapshots:
        return 0

    client = get_supabase_client()
    result = client.table("odds_history").insert(snapshots).execute()
    return len(result.data)


def get_odds_history(
    game_id: str,
    sportsbook: str | None = None,
) -> list[OddsHistory]:
    """Get odds history for a game, optionally filtered by sportsbook."""
    client = get_supabase_client()
    query = client.table("odds_history").select("*").eq("game_id", game_id)
    if sportsbook:
        query = query.eq("sportsbook", sportsbook)
    result = query.order("recorded_at").execute()
    return [OddsHistory(**row) for row in result.data]


def get_latest_odds(game_id: str) -> list[OddsHistory]:
    """Get the most recent odds snapshot for each sportsbook for a game."""
    client = get_supabase_client()
    # Get all records, then deduplicate in Python (Supabase doesn't support DISTINCT ON)
    result = (
        client.table("odds_history")
        .select("*")
        .eq("game_id", game_id)
        .order("recorded_at", desc=True)
        .execute()
    )
    seen: set[tuple[str, str]] = set()
    latest: list[OddsHistory] = []
    for row in result.data:
        key = (row["sportsbook"], row["bet_type"])
        if key not in seen:
            seen.add(key)
            latest.append(OddsHistory(**row))
    return latest


def capture_closing_lines(
    game_id: str,
    sport: str,
    game_start_time: datetime,
) -> dict[str, Any] | None:
    """Capture closing lines for a game (called just before game starts).

    This should be called ~5 minutes before game start to capture
    the final closing odds for CLV calculation.

    Returns:
        Dict with closing line data by bet_type and book, or None if no data
    """
    get_supabase_client()

    # Get the latest odds for this game
    latest = get_latest_odds(game_id)
    if not latest:
        return None

    # Calculate no-vig fair odds for each market

    closing_data: dict[str, Any] = {
        "game_id": game_id,
        "sport": sport,
        "game_start_time": game_start_time.isoformat(),
        "markets": {},
    }

    # Group by bet_type
    by_type: dict[str, list[OddsHistory]] = {}
    for oh in latest:
        by_type.setdefault(oh.bet_type, []).append(oh)

    for bet_type, snapshots in by_type.items():
        market_data: dict[str, Any] = {"books": {}}

        for snap in snapshots:
            market_data["books"][snap.sportsbook] = {
                "line": snap.line,
                "odds": snap.odds,
            }

        # Store to closing_lines table
        for snap in snapshots:
            _store_closing_line(
                game_id=game_id,
                sport=sport,
                bet_type=bet_type,
                sportsbook=snap.sportsbook,
                line=snap.line,
                odds_side1=snap.odds,  # Simplified - would need both sides
                game_start_time=game_start_time,
            )

        closing_data["markets"][bet_type] = market_data

    return closing_data


def _store_closing_line(
    game_id: str,
    sport: str,
    bet_type: str,
    sportsbook: str,
    line: float | None,
    odds_side1: int | None,
    odds_side2: int | None = None,
    fair_prob_side1: float | None = None,
    fair_prob_side2: float | None = None,
    game_start_time: datetime | None = None,
) -> None:
    """Store a closing line record."""
    client = get_supabase_client()

    data = {
        "game_id": game_id,
        "sport": sport,
        "bet_type": bet_type,
        "sportsbook": sportsbook,
    }

    if line is not None:
        data["line"] = line
    if odds_side1 is not None:
        data["odds_side1"] = odds_side1
    if odds_side2 is not None:
        data["odds_side2"] = odds_side2
    if fair_prob_side1 is not None:
        data["fair_prob_side1"] = fair_prob_side1
    if fair_prob_side2 is not None:
        data["fair_prob_side2"] = fair_prob_side2
    if game_start_time is not None:
        data["game_start_time"] = game_start_time.isoformat()

    # Upsert to handle duplicates
    client.table("closing_lines").upsert(data, on_conflict="game_id,sportsbook,bet_type").execute()


def get_closing_line(
    game_id: str,
    bet_type: str,
    sportsbook: str | None = None,
) -> dict[str, Any] | None:
    """Get closing line data for a game.

    Args:
        game_id: Game identifier
        bet_type: Type of bet (spread, total, moneyline)
        sportsbook: Specific sportsbook, or None for consensus

    Returns:
        Dict with closing line data, or None
    """
    client = get_supabase_client()

    query = (
        client.table("closing_lines").select("*").eq("game_id", game_id).eq("bet_type", bet_type)
    )

    if sportsbook:
        query = query.eq("sportsbook", sportsbook)

    result = query.execute()

    if not result.data:
        return None

    if sportsbook:
        return result.data[0]

    # Return consensus (average across books)
    lines = [r["line"] for r in result.data if r.get("line") is not None]
    odds_s1 = [r["odds_side1"] for r in result.data if r.get("odds_side1")]
    odds_s2 = [r["odds_side2"] for r in result.data if r.get("odds_side2")]

    return {
        "game_id": game_id,
        "bet_type": bet_type,
        "consensus_line": sum(lines) / len(lines) if lines else None,
        "avg_odds_side1": int(sum(odds_s1) / len(odds_s1)) if odds_s1 else None,
        "avg_odds_side2": int(sum(odds_s2) / len(odds_s2)) if odds_s2 else None,
        "books_count": len(result.data),
    }


def detect_line_movement(
    game_id: str,
    bet_type: str,
    threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Detect significant line movements for a game.

    Args:
        game_id: Game identifier
        bet_type: Type of bet
        threshold: Minimum movement in points to consider significant

    Returns:
        List of movement events with details
    """
    history = get_odds_history(game_id)

    # Filter to bet_type and sort by time
    filtered = [h for h in history if h.bet_type == bet_type]
    filtered.sort(key=lambda x: x.recorded_at)

    if len(filtered) < 2:
        return []

    movements = []
    prev = filtered[0]

    for curr in filtered[1:]:
        if curr.sportsbook != prev.sportsbook:
            prev = curr
            continue

        if prev.line is not None and curr.line is not None:
            movement = curr.line - prev.line
            if abs(movement) >= threshold:
                movements.append(
                    {
                        "game_id": game_id,
                        "bet_type": bet_type,
                        "sportsbook": curr.sportsbook,
                        "old_line": prev.line,
                        "new_line": curr.line,
                        "movement": movement,
                        "old_odds": prev.odds,
                        "new_odds": curr.odds,
                        "detected_at": curr.recorded_at,
                        "is_significant": abs(movement) >= 1.0,
                    }
                )

        prev = curr

    return movements


def get_line_movement_summary(
    game_id: str,
    bet_type: str,
) -> dict[str, Any]:
    """Get a summary of line movement for a game.

    Returns opening line, current line, and total movement.
    """
    client = get_supabase_client()

    # Get opening line
    opening_result = (
        client.table("opening_lines")
        .select("*")
        .eq("game_id", game_id)
        .eq("bet_type", bet_type)
        .execute()
    )

    # Get latest odds
    latest = get_latest_odds(game_id)
    latest_for_type = [row for row in latest if row.bet_type == bet_type]

    opening_line = None
    if opening_result.data:
        opening_line = opening_result.data[0].get("line")

    current_lines = {}
    for row in latest_for_type:
        current_lines[row.sportsbook] = {
            "line": row.line,
            "odds": row.odds,
        }

    # Calculate average current line
    lines = [v["line"] for v in current_lines.values() if v["line"] is not None]
    avg_current = sum(lines) / len(lines) if lines else None

    total_movement = None
    if opening_line is not None and avg_current is not None:
        total_movement = avg_current - opening_line

    return {
        "game_id": game_id,
        "bet_type": bet_type,
        "opening_line": opening_line,
        "current_line": avg_current,
        "total_movement": total_movement,
        "current_by_book": current_lines,
        "direction": "toward_favorite"
        if total_movement and total_movement < 0
        else "toward_underdog"
        if total_movement and total_movement > 0
        else "unchanged",
    }
