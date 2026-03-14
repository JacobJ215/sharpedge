"""Background job: Scan for +EV betting opportunities.

This job uses two methods for value detection:
1. Model-based: Compares market odds to ML model projections (when available)
2. No-vig consensus: Compares each book's odds to the consensus fair probability

The no-vig method doesn't require ML models and works immediately.
"""

import logging
from datetime import datetime, timezone

from sharpedge_analytics import (
    scan_for_value,
    scan_for_value_no_vig,
    rank_value_plays,
    enrich_with_alpha,
    ValuePlay,
    Confidence,
)
from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha
from sharpedge_bot.services.odds_service import get_odds_client
from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.jobs.value_scanner")

# Store pending value alerts to be dispatched
_pending_value_alerts: list[ValuePlay] = []


def get_pending_value_alerts() -> list[ValuePlay]:
    """Get and clear pending value alerts."""
    global _pending_value_alerts
    alerts = _pending_value_alerts.copy()
    _pending_value_alerts.clear()
    return alerts


async def scan_for_value_plays(bot: object) -> None:
    """Scan for positive EV betting opportunities.

    This job runs every 5 minutes and:
    1. Fetches current odds from all sportsbooks
    2. Uses no-vig consensus to calculate fair probability
    3. Compares each book's odds to fair probability
    4. Optionally enhances with ML projections (when available)
    5. Stores high-value opportunities
    6. Queues alerts for dispatch
    """
    global _pending_value_alerts

    client = get_supabase_client()
    odds_client = get_odds_client()

    sports_to_check = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]
    all_value_plays: list[ValuePlay] = []

    for sport in sports_to_check:
        try:
            odds_data = await odds_client.get_odds(sport)
            if not odds_data:
                continue

            # Primary method: No-vig consensus (works without ML)
            # This compares each book to the market consensus
            no_vig_plays = scan_for_value_no_vig(
                games=odds_data,
                min_ev=1.5,  # 1.5% minimum EV
                min_edge=1.0,  # 1% minimum edge
            )
            all_value_plays.extend(no_vig_plays)

            # Secondary method: Model-based (when projections available)
            projections = await _get_projections(client, sport)
            if projections:
                odds_by_book = _build_odds_by_book(odds_data)
                model_plays = scan_for_value(
                    projections=projections,
                    odds_by_book=odds_by_book,
                    min_ev=2.0,  # Higher threshold for model-based
                    min_edge=1.5,
                )
                # Add model plays, avoiding duplicates
                existing_keys = {(p.game_id, p.sportsbook, p.side) for p in all_value_plays}
                for play in model_plays:
                    if (play.game_id, play.sportsbook, play.side) not in existing_keys:
                        play.notes = "Model-based projection"
                        all_value_plays.append(play)

        except Exception:
            logger.exception("Error scanning for value in %s", sport)

    if not all_value_plays:
        return

    # Enrich with alpha scores then rank by alpha (AGENT-05)
    enriched = enrich_with_alpha(all_value_plays)
    ranked_plays = rank_by_alpha(enriched)
    assert all(p.alpha_score is not None for p in ranked_plays[:20] if ranked_plays), "Alpha enrichment incomplete"

    # Store top plays in database
    stored_count = 0
    for play in ranked_plays[:20]:  # Top 20 plays
        try:
            # Check if we already alerted on this play
            existing = (
                client.table("value_plays")
                .select("id")
                .eq("game_id", play.game_id)
                .eq("bet_type", play.bet_type)
                .eq("side", play.side)
                .eq("sportsbook", play.sportsbook)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

            if existing.data:
                continue  # Already tracking this play

            # Store new value play
            client.table("value_plays").insert({
                "game_id": play.game_id,
                "game": play.game,
                "sport": play.sport,
                "bet_type": play.bet_type,
                "side": play.side,
                "sportsbook": play.sportsbook,
                "market_odds": play.market_odds,
                "model_probability": play.model_probability,
                "implied_probability": play.implied_probability,
                "fair_odds": play.fair_odds,
                "edge_percentage": play.edge_percentage,
                "ev_percentage": play.ev_percentage,
                "confidence": play.confidence,
                "is_active": True,
                "expires_at": play.expires_at.isoformat() if play.expires_at else None,
            }).execute()
            stored_count += 1

            # Queue alert for high confidence plays
            if play.confidence in [Confidence.HIGH, Confidence.MEDIUM]:
                _pending_value_alerts.append(play)

        except Exception as e:
            logger.debug("Failed to store value play: %s", e)

    if stored_count > 0:
        logger.info(
            "Found %d value plays, stored %d new, %d pending alerts",
            len(all_value_plays),
            stored_count,
            len(_pending_value_alerts),
        )


async def _get_projections(client, sport: str) -> list[dict]:
    """Get model projections for a sport.

    Returns projection data formatted for the value scanner.
    """
    try:
        result = (
            client.table("projections")
            .select("*")
            .eq("sport", sport)
            .execute()
        )

        projections = []
        for proj in result.data or []:
            projections.append({
                "game_id": proj.get("game_id", ""),
                "game": f"{proj.get('home_team', '')} vs {proj.get('away_team', '')}",
                "sport": sport,
                "home_team": proj.get("home_team"),
                "away_team": proj.get("away_team"),
                "home_win_prob": proj.get("home_win_prob"),
                "away_win_prob": proj.get("away_win_prob"),
                "spread_home_prob": proj.get("spread_home_prob"),
                "spread_away_prob": proj.get("spread_away_prob"),
                "over_prob": proj.get("over_prob"),
                "under_prob": proj.get("under_prob"),
                "game_time": proj.get("game_time"),
            })

        return projections

    except Exception:
        logger.debug("No projections available for %s", sport)
        return []


def _build_odds_by_book(odds_data: list) -> dict[str, dict]:
    """Build odds structure for value scanner.

    Returns:
        {
            "fanduel": {
                "game_id": {
                    "spread_home": -110,
                    "spread_away": -110,
                    "spread_line": -3.5,
                    "total_over": -110,
                    "total_under": -110,
                    "total_line": 45.5,
                    "ml_home": -150,
                    "ml_away": 130,
                }
            }
        }
    """
    result: dict[str, dict] = {}

    for game in odds_data:
        game_id = game.get("id", "")
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")

        for bookmaker in game.get("bookmakers", []):
            book_key = bookmaker.get("key", "")
            if book_key not in result:
                result[book_key] = {}

            game_odds: dict = {}

            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                outcomes = market.get("outcomes", [])

                if market_key == "spreads":
                    home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                    away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                    if home_out:
                        game_odds["spread_home"] = home_out.get("price", -110)
                        game_odds["spread_line"] = home_out.get("point", 0)
                    if away_out:
                        game_odds["spread_away"] = away_out.get("price", -110)

                elif market_key == "totals":
                    over_out = next((o for o in outcomes if o.get("name") == "Over"), None)
                    under_out = next((o for o in outcomes if o.get("name") == "Under"), None)
                    if over_out:
                        game_odds["total_over"] = over_out.get("price", -110)
                        game_odds["total_line"] = over_out.get("point", 0)
                    if under_out:
                        game_odds["total_under"] = under_out.get("price", -110)

                elif market_key == "h2h":
                    home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                    away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                    if home_out:
                        game_odds["ml_home"] = home_out.get("price", 100)
                    if away_out:
                        game_odds["ml_away"] = away_out.get("price", 100)

            if game_odds:
                result[book_key][game_id] = game_odds

    return result


async def get_active_value_plays(
    sport: str | None = None,
    min_ev: float | None = None,
    confidence: str | None = None,
) -> list[dict]:
    """Get active value plays from database.

    Args:
        sport: Filter by sport
        min_ev: Minimum EV percentage
        confidence: Filter by confidence level

    Returns:
        List of active value plays
    """
    client = get_supabase_client()

    query = (
        client.table("value_plays")
        .select("*")
        .eq("is_active", True)
        .order("ev_percentage", desc=True)
    )

    if sport:
        query = query.eq("sport", sport)

    if min_ev:
        query = query.gte("ev_percentage", min_ev)

    if confidence:
        query = query.eq("confidence", confidence)

    result = query.limit(50).execute()
    return result.data or []
