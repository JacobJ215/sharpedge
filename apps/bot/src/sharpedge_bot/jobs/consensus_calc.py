"""Background job: Calculate and store consensus lines."""

import logging
from datetime import datetime, timezone

from sharpedge_analytics import (
    calculate_weighted_consensus,
    calculate_fair_odds,
    calculate_market_agreement,
)
from sharpedge_bot.services.odds_service import get_odds_client
from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.jobs.consensus")


async def calculate_consensus(bot: object) -> None:
    """Calculate consensus lines for all active games.

    This job runs every 5 minutes and:
    1. Fetches current odds from all sportsbooks
    2. Calculates median/weighted consensus
    3. Calculates no-vig fair probabilities
    4. Stores results for quick retrieval
    """
    client = get_supabase_client()
    odds_client = get_odds_client()

    updated_count = 0
    sports_to_check = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]

    for sport in sports_to_check:
        try:
            odds_data = await odds_client.get_odds(sport)
            if not odds_data:
                continue

            for game in odds_data:
                game_id = game.get("id", "")
                if not game_id:
                    continue

                consensus_data = _calculate_game_consensus(game)
                if not consensus_data:
                    continue

                # Upsert consensus data
                try:
                    client.table("consensus_lines").upsert(
                        {
                            "game_id": game_id,
                            "sport": sport,
                            **consensus_data,
                            "calculated_at": datetime.now(timezone.utc).isoformat(),
                        },
                        on_conflict="game_id",
                    ).execute()
                    updated_count += 1
                except Exception as e:
                    logger.debug("Failed to store consensus: %s", e)

        except Exception:
            logger.exception("Error calculating consensus for %s", sport)

    if updated_count > 0:
        logger.info("Updated consensus for %d games", updated_count)


def _calculate_game_consensus(game: dict) -> dict | None:
    """Calculate consensus for a single game."""
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return None

    home_team = game.get("home_team", "")
    away_team = game.get("away_team", "")

    # Collect lines by type
    spread_lines: dict[str, float] = {}
    total_lines: dict[str, float] = {}
    spread_odds_home: dict[str, int] = {}
    spread_odds_away: dict[str, int] = {}
    total_odds_over: dict[str, int] = {}
    total_odds_under: dict[str, int] = {}
    ml_odds_home: dict[str, int] = {}
    ml_odds_away: dict[str, int] = {}

    for bookmaker in bookmakers:
        book_key = bookmaker.get("key", "")

        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            outcomes = market.get("outcomes", [])

            if market_key == "spreads":
                home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                if home_out:
                    spread_lines[book_key] = home_out.get("point", 0)
                    spread_odds_home[book_key] = home_out.get("price", -110)
                if away_out:
                    spread_odds_away[book_key] = away_out.get("price", -110)

            elif market_key == "totals":
                over_out = next((o for o in outcomes if o.get("name") == "Over"), None)
                under_out = next((o for o in outcomes if o.get("name") == "Under"), None)
                if over_out:
                    total_lines[book_key] = over_out.get("point", 0)
                    total_odds_over[book_key] = over_out.get("price", -110)
                if under_out:
                    total_odds_under[book_key] = under_out.get("price", -110)

            elif market_key == "h2h":
                home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                if home_out:
                    ml_odds_home[book_key] = home_out.get("price", 100)
                if away_out:
                    ml_odds_away[book_key] = away_out.get("price", 100)

    result = {}

    # Spread consensus
    if spread_lines:
        spread_consensus = calculate_weighted_consensus(spread_lines)
        result["spread_consensus"] = spread_consensus.median_line
        result["spread_weighted_consensus"] = spread_consensus.weighted_consensus
        result["spread_min"] = spread_consensus.min_line
        result["spread_max"] = spread_consensus.max_line
        result["spread_books_count"] = spread_consensus.books_count

        # Calculate fair probability using median odds
        if spread_odds_home and spread_odds_away:
            median_home = list(spread_odds_home.values())[len(spread_odds_home) // 2]
            median_away = list(spread_odds_away.values())[len(spread_odds_away) // 2]
            fair = calculate_fair_odds(median_home, median_away)
            result["spread_fair_home_prob"] = fair.fair_prob_a
            result["spread_fair_away_prob"] = fair.fair_prob_b

    # Total consensus
    if total_lines:
        total_consensus = calculate_weighted_consensus(total_lines)
        result["total_consensus"] = total_consensus.median_line
        result["total_weighted_consensus"] = total_consensus.weighted_consensus
        result["total_min"] = total_consensus.min_line
        result["total_max"] = total_consensus.max_line
        result["total_books_count"] = total_consensus.books_count

        if total_odds_over and total_odds_under:
            median_over = list(total_odds_over.values())[len(total_odds_over) // 2]
            median_under = list(total_odds_under.values())[len(total_odds_under) // 2]
            fair = calculate_fair_odds(median_over, median_under)
            result["total_fair_over_prob"] = fair.fair_prob_a
            result["total_fair_under_prob"] = fair.fair_prob_b

    # ML fair odds
    if ml_odds_home and ml_odds_away:
        median_home = list(ml_odds_home.values())[len(ml_odds_home) // 2]
        median_away = list(ml_odds_away.values())[len(ml_odds_away) // 2]
        fair = calculate_fair_odds(median_home, median_away)
        result["ml_fair_home_prob"] = fair.fair_prob_a
        result["ml_fair_away_prob"] = fair.fair_prob_b

    # Market agreement (how much books agree)
    if spread_lines:
        result["market_agreement"] = calculate_market_agreement(list(spread_lines.values()))

    return result if result else None


async def get_consensus(game_id: str) -> dict | None:
    """Get consensus data for a game.

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
