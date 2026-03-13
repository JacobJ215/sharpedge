"""Background job: Capture opening lines when games first appear."""

import logging
from datetime import datetime, timezone

from sharpedge_bot.services.odds_service import get_odds_client
from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.jobs.opening_lines")

# Track which games we've already captured opening lines for
_captured_games: set[str] = set()


async def capture_opening_lines(bot: object) -> None:
    """Capture opening lines for any new games.

    This job runs every 30 minutes and checks for games we haven't
    seen before. When a new game appears, we store its first odds
    as the "opening line".
    """
    client = get_supabase_client()
    odds_client = get_odds_client()

    captured_count = 0
    sports_to_check = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]

    for sport in sports_to_check:
        try:
            odds_data = await odds_client.get_odds(sport)
            if not odds_data:
                continue

            for game in odds_data:
                game_id = game.get("id", "")
                if not game_id or game_id in _captured_games:
                    continue

                # Check if we already have opening lines for this game
                existing = (
                    client.table("opening_lines")
                    .select("id")
                    .eq("game_id", game_id)
                    .limit(1)
                    .execute()
                )

                if existing.data:
                    _captured_games.add(game_id)
                    continue

                # New game - capture opening lines
                home_team = game.get("home_team", "")
                away_team = game.get("away_team", "")
                game_time = game.get("commence_time")

                for bookmaker in game.get("bookmakers", []):
                    book_name = bookmaker.get("key", "")

                    for market in bookmaker.get("markets", []):
                        market_key = market.get("key", "")
                        outcomes = market.get("outcomes", [])

                        if market_key == "spreads":
                            _store_spread_opening(
                                client, game_id, sport, home_team, away_team,
                                book_name, outcomes, game_time
                            )
                            captured_count += 1

                        elif market_key == "totals":
                            _store_total_opening(
                                client, game_id, sport, home_team, away_team,
                                book_name, outcomes, game_time
                            )
                            captured_count += 1

                        elif market_key == "h2h":
                            _store_moneyline_opening(
                                client, game_id, sport, home_team, away_team,
                                book_name, outcomes, game_time
                            )
                            captured_count += 1

                _captured_games.add(game_id)

        except Exception:
            logger.exception("Error capturing opening lines for %s", sport)

    if captured_count > 0:
        logger.info("Captured %d opening lines across %d sports", captured_count, len(sports_to_check))


def _store_spread_opening(
    client,
    game_id: str,
    sport: str,
    home_team: str,
    away_team: str,
    book_name: str,
    outcomes: list,
    game_time: str | None,
):
    """Store spread opening line."""
    home_outcome = next((o for o in outcomes if o.get("name") == home_team), None)
    away_outcome = next((o for o in outcomes if o.get("name") == away_team), None)

    if not home_outcome or not away_outcome:
        return

    try:
        client.table("opening_lines").insert({
            "game_id": game_id,
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "sportsbook": book_name,
            "bet_type": "spread",
            "line": home_outcome.get("point", 0),
            "odds_a": home_outcome.get("price", -110),
            "odds_b": away_outcome.get("price", -110),
            "game_start_time": game_time,
        }).execute()
    except Exception as e:
        logger.debug("Failed to store spread opening: %s", e)


def _store_total_opening(
    client,
    game_id: str,
    sport: str,
    home_team: str,
    away_team: str,
    book_name: str,
    outcomes: list,
    game_time: str | None,
):
    """Store total opening line."""
    over_outcome = next((o for o in outcomes if o.get("name") == "Over"), None)
    under_outcome = next((o for o in outcomes if o.get("name") == "Under"), None)

    if not over_outcome or not under_outcome:
        return

    try:
        client.table("opening_lines").insert({
            "game_id": game_id,
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "sportsbook": book_name,
            "bet_type": "total",
            "line": over_outcome.get("point", 0),
            "odds_a": over_outcome.get("price", -110),
            "odds_b": under_outcome.get("price", -110),
            "game_start_time": game_time,
        }).execute()
    except Exception as e:
        logger.debug("Failed to store total opening: %s", e)


def _store_moneyline_opening(
    client,
    game_id: str,
    sport: str,
    home_team: str,
    away_team: str,
    book_name: str,
    outcomes: list,
    game_time: str | None,
):
    """Store moneyline opening line."""
    home_outcome = next((o for o in outcomes if o.get("name") == home_team), None)
    away_outcome = next((o for o in outcomes if o.get("name") == away_team), None)

    if not home_outcome or not away_outcome:
        return

    try:
        client.table("opening_lines").insert({
            "game_id": game_id,
            "sport": sport,
            "home_team": home_team,
            "away_team": away_team,
            "sportsbook": book_name,
            "bet_type": "moneyline",
            "line": None,
            "odds_a": home_outcome.get("price", 100),
            "odds_b": away_outcome.get("price", 100),
            "game_start_time": game_time,
        }).execute()
    except Exception as e:
        logger.debug("Failed to store moneyline opening: %s", e)


async def get_opening_line(game_id: str, bet_type: str = "spread") -> dict | None:
    """Retrieve opening line for a game.

    Args:
        game_id: Game identifier
        bet_type: 'spread', 'total', or 'moneyline'

    Returns:
        Opening line data or None
    """
    client = get_supabase_client()

    result = (
        client.table("opening_lines")
        .select("*")
        .eq("game_id", game_id)
        .eq("bet_type", bet_type)
        .order("captured_at")
        .limit(1)
        .execute()
    )

    return result.data[0] if result.data else None


async def calculate_movement_from_open(
    game_id: str,
    current_line: float,
    bet_type: str = "spread",
) -> dict | None:
    """Calculate line movement from opening to current.

    Args:
        game_id: Game identifier
        current_line: Current line value
        bet_type: Type of bet

    Returns:
        Movement analysis or None
    """
    opening = await get_opening_line(game_id, bet_type)
    if not opening:
        return None

    opening_line = opening.get("line", 0) or 0
    movement = current_line - opening_line

    return {
        "opening_line": opening_line,
        "current_line": current_line,
        "movement": movement,
        "direction": "toward_favorite" if movement < 0 else "toward_underdog",
        "captured_at": opening.get("captured_at"),
    }
