"""Database queries for opening lines."""

from datetime import datetime
from typing import Any

from sharpedge_db.client import get_supabase_client


def store_opening_line(
    game_id: str,
    sport: str,
    home_team: str,
    away_team: str,
    sportsbook: str,
    bet_type: str,
    line: float | None,
    odds_a: int,
    odds_b: int,
    game_start_time: datetime | None = None,
) -> dict | None:
    """Store an opening line.

    Args:
        game_id: Unique game identifier
        sport: Sport code
        home_team: Home team name
        away_team: Away team name
        sportsbook: Sportsbook key
        bet_type: 'spread', 'total', or 'moneyline'
        line: Line value (spread or total number, None for ML)
        odds_a: Odds for side A
        odds_b: Odds for side B
        game_start_time: When the game starts

    Returns:
        Created record or None
    """
    client = get_supabase_client()

    try:
        result = client.table("opening_lines").upsert(
            {
                "game_id": game_id,
                "sport": sport,
                "home_team": home_team,
                "away_team": away_team,
                "sportsbook": sportsbook,
                "bet_type": bet_type,
                "line": line,
                "odds_a": odds_a,
                "odds_b": odds_b,
                "game_start_time": game_start_time.isoformat() if game_start_time else None,
            },
            on_conflict="game_id,sportsbook,bet_type",
        ).execute()

        return result.data[0] if result.data else None
    except Exception:
        return None


def get_opening_line(
    game_id: str,
    bet_type: str = "spread",
    sportsbook: str | None = None,
) -> dict | None:
    """Get opening line for a game.

    Args:
        game_id: Game identifier
        bet_type: Type of bet
        sportsbook: Specific book (optional, returns first if not specified)

    Returns:
        Opening line data or None
    """
    client = get_supabase_client()

    query = (
        client.table("opening_lines")
        .select("*")
        .eq("game_id", game_id)
        .eq("bet_type", bet_type)
    )

    if sportsbook:
        query = query.eq("sportsbook", sportsbook)

    result = query.order("captured_at").limit(1).execute()

    return result.data[0] if result.data else None


def get_all_opening_lines(game_id: str) -> list[dict]:
    """Get all opening lines for a game across all books and bet types.

    Args:
        game_id: Game identifier

    Returns:
        List of opening line records
    """
    client = get_supabase_client()

    result = (
        client.table("opening_lines")
        .select("*")
        .eq("game_id", game_id)
        .execute()
    )

    return result.data or []


def calculate_movement_from_open(
    game_id: str,
    current_line: float,
    bet_type: str = "spread",
) -> dict | None:
    """Calculate movement from opening line.

    Args:
        game_id: Game identifier
        current_line: Current line value
        bet_type: Type of bet

    Returns:
        Movement analysis or None
    """
    opening = get_opening_line(game_id, bet_type)
    if not opening:
        return None

    opening_line = opening.get("line") or 0
    movement = current_line - opening_line

    if bet_type == "spread":
        if movement < 0:
            direction = "toward_favorite"
            interpretation = f"Favorite now getting {abs(movement):.1f} fewer points"
        elif movement > 0:
            direction = "toward_underdog"
            interpretation = f"Underdog now getting {movement:.1f} more points"
        else:
            direction = "unchanged"
            interpretation = "Line unchanged from open"
    else:
        if movement < 0:
            direction = "down"
            interpretation = f"Total dropped {abs(movement):.1f} points"
        elif movement > 0:
            direction = "up"
            interpretation = f"Total rose {movement:.1f} points"
        else:
            direction = "unchanged"
            interpretation = "Total unchanged from open"

    return {
        "game_id": game_id,
        "opening_line": opening_line,
        "current_line": current_line,
        "movement": round(movement, 2),
        "direction": direction,
        "interpretation": interpretation,
        "significance": "major" if abs(movement) >= 1.5 else "notable" if abs(movement) >= 0.5 else "minor",
        "opening_odds_a": opening.get("odds_a"),
        "opening_odds_b": opening.get("odds_b"),
        "captured_at": opening.get("captured_at"),
    }
