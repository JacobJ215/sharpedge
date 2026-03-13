"""Database queries for consensus lines."""

from datetime import datetime, timezone
from typing import Any

from sharpedge_db.client import get_supabase_client


def store_consensus(
    game_id: str,
    sport: str,
    spread_consensus: float | None = None,
    spread_weighted_consensus: float | None = None,
    spread_min: float | None = None,
    spread_max: float | None = None,
    spread_books_count: int | None = None,
    total_consensus: float | None = None,
    total_weighted_consensus: float | None = None,
    total_min: float | None = None,
    total_max: float | None = None,
    total_books_count: int | None = None,
    spread_fair_home_prob: float | None = None,
    spread_fair_away_prob: float | None = None,
    total_fair_over_prob: float | None = None,
    total_fair_under_prob: float | None = None,
    ml_fair_home_prob: float | None = None,
    ml_fair_away_prob: float | None = None,
    market_agreement: float | None = None,
) -> dict | None:
    """Store or update consensus line data.

    Args:
        game_id: Game identifier
        sport: Sport code
        spread_consensus: Median spread across books
        spread_weighted_consensus: Weighted spread (by book sharpness)
        spread_min: Minimum spread (best for favorite)
        spread_max: Maximum spread (best for underdog)
        spread_books_count: Number of books in spread calculation
        total_consensus: Median total
        total_weighted_consensus: Weighted total
        total_min: Minimum total
        total_max: Maximum total
        total_books_count: Number of books in total calculation
        spread_fair_home_prob: No-vig probability home covers
        spread_fair_away_prob: No-vig probability away covers
        total_fair_over_prob: No-vig probability over hits
        total_fair_under_prob: No-vig probability under hits
        ml_fair_home_prob: No-vig probability home wins
        ml_fair_away_prob: No-vig probability away wins
        market_agreement: How much books agree (0-100)

    Returns:
        Created/updated record or None
    """
    client = get_supabase_client()

    data = {
        "game_id": game_id,
        "sport": sport,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Only include non-None values
    optional_fields = {
        "spread_consensus": spread_consensus,
        "spread_weighted_consensus": spread_weighted_consensus,
        "spread_min": spread_min,
        "spread_max": spread_max,
        "spread_books_count": spread_books_count,
        "total_consensus": total_consensus,
        "total_weighted_consensus": total_weighted_consensus,
        "total_min": total_min,
        "total_max": total_max,
        "total_books_count": total_books_count,
        "spread_fair_home_prob": spread_fair_home_prob,
        "spread_fair_away_prob": spread_fair_away_prob,
        "total_fair_over_prob": total_fair_over_prob,
        "total_fair_under_prob": total_fair_under_prob,
        "ml_fair_home_prob": ml_fair_home_prob,
        "ml_fair_away_prob": ml_fair_away_prob,
        "market_agreement": market_agreement,
    }

    for key, value in optional_fields.items():
        if value is not None:
            data[key] = value

    try:
        result = client.table("consensus_lines").upsert(
            data,
            on_conflict="game_id",
        ).execute()

        return result.data[0] if result.data else None
    except Exception:
        return None


def get_consensus(game_id: str) -> dict | None:
    """Get latest consensus for a game.

    Args:
        game_id: Game identifier

    Returns:
        Consensus data or None
    """
    client = get_supabase_client()

    result = (
        client.table("consensus_lines")
        .select("*")
        .eq("game_id", game_id)
        .order("calculated_at", desc=True)
        .limit(1)
        .execute()
    )

    return result.data[0] if result.data else None


def get_fair_probabilities(game_id: str) -> dict | None:
    """Get no-vig fair probabilities for a game.

    Args:
        game_id: Game identifier

    Returns:
        Dict with fair probabilities for all bet types
    """
    consensus = get_consensus(game_id)
    if not consensus:
        return None

    return {
        "spread": {
            "home": consensus.get("spread_fair_home_prob"),
            "away": consensus.get("spread_fair_away_prob"),
        },
        "total": {
            "over": consensus.get("total_fair_over_prob"),
            "under": consensus.get("total_fair_under_prob"),
        },
        "moneyline": {
            "home": consensus.get("ml_fair_home_prob"),
            "away": consensus.get("ml_fair_away_prob"),
        },
    }


def get_market_disagreement(sport: str | None = None) -> list[dict]:
    """Find games where books disagree most (opportunity).

    Args:
        sport: Filter by sport (optional)

    Returns:
        List of games sorted by market disagreement
    """
    client = get_supabase_client()

    query = (
        client.table("consensus_lines")
        .select("game_id, sport, spread_min, spread_max, total_min, total_max, market_agreement")
        .order("market_agreement")
        .limit(20)
    )

    if sport:
        query = query.eq("sport", sport)

    result = query.execute()

    games = []
    for row in result.data or []:
        spread_range = (row.get("spread_max") or 0) - (row.get("spread_min") or 0)
        total_range = (row.get("total_max") or 0) - (row.get("total_min") or 0)

        games.append({
            "game_id": row["game_id"],
            "sport": row["sport"],
            "spread_range": round(spread_range, 1),
            "total_range": round(total_range, 1),
            "market_agreement": row.get("market_agreement"),
        })

    return games
