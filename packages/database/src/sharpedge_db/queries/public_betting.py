"""Database queries for public betting data."""

from datetime import datetime, timezone
from typing import Any

from sharpedge_db.client import get_supabase_client


def store_public_betting(
    game_id: str,
    sport: str,
    home_team: str | None = None,
    away_team: str | None = None,
    spread_ticket_home: float | None = None,
    spread_ticket_away: float | None = None,
    spread_money_home: float | None = None,
    spread_money_away: float | None = None,
    total_ticket_over: float | None = None,
    total_ticket_under: float | None = None,
    total_money_over: float | None = None,
    total_money_under: float | None = None,
    ml_ticket_home: float | None = None,
    ml_ticket_away: float | None = None,
    ml_money_home: float | None = None,
    ml_money_away: float | None = None,
    spread_sharp_side: str | None = None,
    spread_divergence: float | None = None,
    total_sharp_side: str | None = None,
    total_divergence: float | None = None,
    source: str = "manual",
) -> dict | None:
    """Store public betting data.

    Args:
        game_id: Game identifier
        sport: Sport code
        home_team: Home team name
        away_team: Away team name
        spread_ticket_home: % of tickets on home spread
        spread_ticket_away: % of tickets on away spread
        spread_money_home: % of money on home spread
        spread_money_away: % of money on away spread
        total_ticket_over: % of tickets on over
        total_ticket_under: % of tickets on under
        total_money_over: % of money on over
        total_money_under: % of money on under
        ml_ticket_home: % of tickets on home ML
        ml_ticket_away: % of tickets on away ML
        ml_money_home: % of money on home ML
        ml_money_away: % of money on away ML
        spread_sharp_side: Detected sharp side for spread
        spread_divergence: Money/ticket divergence for spread
        total_sharp_side: Detected sharp side for total
        total_divergence: Money/ticket divergence for total
        source: Data source

    Returns:
        Created record or None
    """
    client = get_supabase_client()

    data = {
        "game_id": game_id,
        "sport": sport,
        "source": source,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }

    optional_fields = {
        "home_team": home_team,
        "away_team": away_team,
        "spread_ticket_home": spread_ticket_home,
        "spread_ticket_away": spread_ticket_away,
        "spread_money_home": spread_money_home,
        "spread_money_away": spread_money_away,
        "total_ticket_over": total_ticket_over,
        "total_ticket_under": total_ticket_under,
        "total_money_over": total_money_over,
        "total_money_under": total_money_under,
        "ml_ticket_home": ml_ticket_home,
        "ml_ticket_away": ml_ticket_away,
        "ml_money_home": ml_money_home,
        "ml_money_away": ml_money_away,
        "spread_sharp_side": spread_sharp_side,
        "spread_divergence": spread_divergence,
        "total_sharp_side": total_sharp_side,
        "total_divergence": total_divergence,
    }

    for key, value in optional_fields.items():
        if value is not None:
            data[key] = value

    try:
        result = client.table("public_betting").insert(data).execute()
        return result.data[0] if result.data else None
    except Exception:
        return None


def get_public_betting(game_id: str) -> dict | None:
    """Get latest public betting data for a game.

    Args:
        game_id: Game identifier

    Returns:
        Public betting data or None
    """
    client = get_supabase_client()

    result = (
        client.table("public_betting")
        .select("*")
        .eq("game_id", game_id)
        .order("captured_at", desc=True)
        .limit(1)
        .execute()
    )

    return result.data[0] if result.data else None


def get_sharp_plays(
    min_divergence: float = 10,
    min_public_pct: float = 65,
    sport: str | None = None,
) -> list[dict]:
    """Find games with sharp money signals.

    Args:
        min_divergence: Minimum money/ticket divergence
        min_public_pct: Minimum public ticket percentage
        sport: Filter by sport

    Returns:
        List of games with sharp signals
    """
    client = get_supabase_client()

    # Get latest public betting for each game
    query = (
        client.table("public_betting")
        .select("*")
        .gte("spread_divergence", min_divergence)
        .order("captured_at", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.limit(50).execute()

    sharp_plays = []
    seen_games = set()

    for row in result.data or []:
        game_id = row["game_id"]
        if game_id in seen_games:
            continue
        seen_games.add(game_id)

        # Check if public percentage is high enough
        spread_public_pct = max(
            row.get("spread_ticket_home") or 0,
            row.get("spread_ticket_away") or 0,
        )

        if spread_public_pct >= min_public_pct:
            sharp_plays.append({
                "game_id": game_id,
                "sport": row["sport"],
                "home_team": row.get("home_team"),
                "away_team": row.get("away_team"),
                "public_side": "home" if (row.get("spread_ticket_home") or 0) > 50 else "away",
                "public_pct": spread_public_pct,
                "sharp_side": row.get("spread_sharp_side"),
                "divergence": row.get("spread_divergence"),
                "captured_at": row["captured_at"],
            })

    return sorted(sharp_plays, key=lambda x: x.get("divergence") or 0, reverse=True)


def get_contrarian_plays(
    min_public_pct: float = 70,
    sport: str | None = None,
) -> list[dict]:
    """Find games where public is heavily on one side.

    Good for fade-the-public strategies.

    Args:
        min_public_pct: Minimum public percentage to consider
        sport: Filter by sport

    Returns:
        List of lopsided games
    """
    client = get_supabase_client()

    query = (
        client.table("public_betting")
        .select("*")
        .order("captured_at", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.limit(100).execute()

    contrarian_plays = []
    seen_games = set()

    for row in result.data or []:
        game_id = row["game_id"]
        if game_id in seen_games:
            continue
        seen_games.add(game_id)

        # Check spread
        spread_home = row.get("spread_ticket_home") or 50
        spread_away = row.get("spread_ticket_away") or 50
        if max(spread_home, spread_away) >= min_public_pct:
            contrarian_plays.append({
                "game_id": game_id,
                "sport": row["sport"],
                "bet_type": "spread",
                "public_side": "home" if spread_home > spread_away else "away",
                "public_pct": max(spread_home, spread_away),
                "fade_side": "away" if spread_home > spread_away else "home",
            })

        # Check total
        total_over = row.get("total_ticket_over") or 50
        total_under = row.get("total_ticket_under") or 50
        if max(total_over, total_under) >= min_public_pct:
            contrarian_plays.append({
                "game_id": game_id,
                "sport": row["sport"],
                "bet_type": "total",
                "public_side": "over" if total_over > total_under else "under",
                "public_pct": max(total_over, total_under),
                "fade_side": "under" if total_over > total_under else "over",
            })

    return sorted(contrarian_plays, key=lambda x: x["public_pct"], reverse=True)
