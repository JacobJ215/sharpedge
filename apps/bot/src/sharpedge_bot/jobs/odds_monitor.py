"""Background job: Monitor odds changes and detect significant movements."""

import logging
import os

from sharpedge_db.queries.odds_history import get_latest_odds, store_odds_snapshot
from sharpedge_shared.constants import LINE_MOVEMENT_THRESHOLD
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.jobs.odds_monitor")

# Tracks alerts to avoid duplicates within a run
_pending_alerts: list[dict] = []


async def monitor_odds(bot: object) -> None:
    """Fetch current odds, compare to previous, store history, detect movements."""
    api_key = os.environ.get("ODDS_API_KEY", "")
    redis_url = os.environ.get("REDIS_URL", "")

    if not api_key:
        logger.debug("Odds API key not configured, skipping monitor.")
        return

    from sharpedge_bot.services.odds_service import get_odds_client

    client = get_odds_client(api_key, redis_url)
    _pending_alerts.clear()

    # Monitor active sports
    active_sports = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]

    for sport in active_sports:
        try:
            games = client.get_odds(sport, markets=["spreads", "totals"])
        except Exception:
            logger.debug("Failed to fetch odds for %s.", sport)
            continue

        for game in games:
            for bookmaker in game.bookmakers:
                for market in bookmaker.markets:
                    for outcome in market.outcomes:
                        # Store current snapshot
                        store_odds_snapshot(
                            game_id=game.id,
                            sportsbook=bookmaker.key,
                            bet_type=f"{market.key}_{outcome.name}",
                            line=outcome.point,
                            odds=outcome.price,
                        )

            # Check for significant line movement
            _check_movement(game)

    logger.info("Odds monitor complete. %d potential alerts detected.", len(_pending_alerts))


def _check_movement(game: object) -> None:
    """Check if a game has significant line movement."""
    # Get previous odds for this game
    previous = get_latest_odds(game.id)
    if not previous:
        return

    # Compare consensus spread to previous
    # This is simplified — production would track opening line and aggregate
    for prev in previous:
        if prev.bet_type.startswith("spreads_") and prev.line is not None:
            # Find current line for same book/type from game data
            for book in game.bookmakers:
                if book.key == prev.sportsbook:
                    for market in book.markets:
                        if market.key == "spreads":
                            for outcome in market.outcomes:
                                if (
                                    f"spreads_{outcome.name}" == prev.bet_type
                                    and outcome.point is not None
                                ):
                                    movement = abs(float(outcome.point) - float(prev.line))
                                    if movement >= LINE_MOVEMENT_THRESHOLD:
                                        _pending_alerts.append(
                                            {
                                                "type": "movement",
                                                "game_id": game.id,
                                                "game": f"{game.away_team} @ {game.home_team}",
                                                "old_line": float(prev.line),
                                                "new_line": float(outcome.point),
                                                "sportsbook": book.key,
                                                "movement": movement,
                                            }
                                        )


def get_pending_alerts() -> list[dict]:
    """Get alerts detected in the most recent monitor run."""
    return list(_pending_alerts)
