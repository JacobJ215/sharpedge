"""Background job: Detect arbitrage opportunities."""

import logging
from datetime import datetime, timezone

from sharpedge_analytics import (
    scan_for_arbitrage,
    find_best_arb_combo,
    ArbitrageResult,
)
from sharpedge_bot.services.odds_service import get_odds_client
from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.jobs.arbitrage")

# Store pending arbitrage alerts
_pending_arb_alerts: list[dict] = []


def get_pending_arb_alerts() -> list[dict]:
    """Get and clear pending arbitrage alerts."""
    global _pending_arb_alerts
    alerts = _pending_arb_alerts.copy()
    _pending_arb_alerts.clear()
    return alerts


async def scan_for_arbitrage_opportunities(bot: object) -> None:
    """Scan for arbitrage opportunities across sportsbooks.

    This job runs every 5 minutes and:
    1. Fetches current odds from all sportsbooks
    2. Checks all book combinations for arb opportunities
    3. Stores and alerts on profitable opportunities
    """
    global _pending_arb_alerts

    client = get_supabase_client()
    odds_client = get_odds_client()

    sports_to_check = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]
    all_arbs: list[dict] = []

    for sport in sports_to_check:
        try:
            odds_data = await odds_client.get_odds(sport)
            if not odds_data:
                continue

            for game in odds_data:
                game_id = game.get("id", "")
                home_team = game.get("home_team", "")
                away_team = game.get("away_team", "")
                game_desc = f"{away_team} @ {home_team}"

                # Check each market type for arbs
                arbs = _check_game_for_arbs(game, game_id, game_desc, sport)
                all_arbs.extend(arbs)

        except Exception:
            logger.exception("Error scanning for arbitrage in %s", sport)

    if not all_arbs:
        return

    # Sort by profit percentage
    all_arbs.sort(key=lambda x: x["profit_percentage"], reverse=True)

    # Store and alert
    stored_count = 0
    for arb in all_arbs[:10]:  # Top 10 arbs
        try:
            # Check if already tracking this arb
            existing = (
                client.table("arbitrage_opportunities")
                .select("id")
                .eq("game_id", arb["game_id"])
                .eq("bet_type", arb["bet_type"])
                .eq("book_a", arb["book_a"])
                .eq("book_b", arb["book_b"])
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

            if existing.data:
                continue

            # Store new arb
            client.table("arbitrage_opportunities").insert({
                "game_id": arb["game_id"],
                "game": arb["game"],
                "sport": arb["sport"],
                "bet_type": arb["bet_type"],
                "book_a": arb["book_a"],
                "side_a": arb["side_a"],
                "odds_a": arb["odds_a"],
                "stake_a_percentage": arb["stake_a_percentage"],
                "book_b": arb["book_b"],
                "side_b": arb["side_b"],
                "odds_b": arb["odds_b"],
                "stake_b_percentage": arb["stake_b_percentage"],
                "profit_percentage": arb["profit_percentage"],
                "total_implied": arb["total_implied"],
                "is_active": True,
            }).execute()
            stored_count += 1

            # Queue alert
            if arb["profit_percentage"] >= 1.0:  # 1%+ profit worth alerting
                _pending_arb_alerts.append(arb)

        except Exception as e:
            logger.debug("Failed to store arb: %s", e)

    if stored_count > 0:
        logger.info(
            "Found %d arbs, stored %d new, %d pending alerts",
            len(all_arbs),
            stored_count,
            len(_pending_arb_alerts),
        )


def _check_game_for_arbs(
    game: dict,
    game_id: str,
    game_desc: str,
    sport: str,
) -> list[dict]:
    """Check a single game for arbitrage opportunities."""
    arbs = []
    home_team = game.get("home_team", "")
    away_team = game.get("away_team", "")

    # Collect odds by market
    spread_home: dict[str, int] = {}
    spread_away: dict[str, int] = {}
    total_over: dict[str, int] = {}
    total_under: dict[str, int] = {}
    ml_home: dict[str, int] = {}
    ml_away: dict[str, int] = {}

    for bookmaker in game.get("bookmakers", []):
        book_key = bookmaker.get("key", "")

        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            outcomes = market.get("outcomes", [])

            if market_key == "spreads":
                home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                if home_out:
                    spread_home[book_key] = home_out.get("price", -110)
                if away_out:
                    spread_away[book_key] = away_out.get("price", -110)

            elif market_key == "totals":
                over_out = next((o for o in outcomes if o.get("name") == "Over"), None)
                under_out = next((o for o in outcomes if o.get("name") == "Under"), None)
                if over_out:
                    total_over[book_key] = over_out.get("price", -110)
                if under_out:
                    total_under[book_key] = under_out.get("price", -110)

            elif market_key == "h2h":
                home_out = next((o for o in outcomes if o.get("name") == home_team), None)
                away_out = next((o for o in outcomes if o.get("name") == away_team), None)
                if home_out:
                    ml_home[book_key] = home_out.get("price", 100)
                if away_out:
                    ml_away[book_key] = away_out.get("price", 100)

    # Check spread arbs
    if spread_home and spread_away:
        spread_arbs = scan_for_arbitrage(spread_home, spread_away)
        for arb in spread_arbs:
            arbs.append({
                "game_id": game_id,
                "game": game_desc,
                "sport": sport,
                "bet_type": "spread",
                "book_a": arb.book_a,
                "side_a": f"{home_team} spread",
                "odds_a": arb.odds_a,
                "stake_a_percentage": arb.stake_a_percentage,
                "book_b": arb.book_b,
                "side_b": f"{away_team} spread",
                "odds_b": arb.odds_b,
                "stake_b_percentage": arb.stake_b_percentage,
                "profit_percentage": arb.profit_percentage,
                "total_implied": arb.total_implied,
            })

    # Check total arbs
    if total_over and total_under:
        total_arbs = scan_for_arbitrage(total_over, total_under)
        for arb in total_arbs:
            arbs.append({
                "game_id": game_id,
                "game": game_desc,
                "sport": sport,
                "bet_type": "total",
                "book_a": arb.book_a,
                "side_a": "Over",
                "odds_a": arb.odds_a,
                "stake_a_percentage": arb.stake_a_percentage,
                "book_b": arb.book_b,
                "side_b": "Under",
                "odds_b": arb.odds_b,
                "stake_b_percentage": arb.stake_b_percentage,
                "profit_percentage": arb.profit_percentage,
                "total_implied": arb.total_implied,
            })

    # Check moneyline arbs
    if ml_home and ml_away:
        ml_arbs = scan_for_arbitrage(ml_home, ml_away)
        for arb in ml_arbs:
            arbs.append({
                "game_id": game_id,
                "game": game_desc,
                "sport": sport,
                "bet_type": "moneyline",
                "book_a": arb.book_a,
                "side_a": f"{home_team} ML",
                "odds_a": arb.odds_a,
                "stake_a_percentage": arb.stake_a_percentage,
                "book_b": arb.book_b,
                "side_b": f"{away_team} ML",
                "odds_b": arb.odds_b,
                "stake_b_percentage": arb.stake_b_percentage,
                "profit_percentage": arb.profit_percentage,
                "total_implied": arb.total_implied,
            })

    return arbs


async def get_active_arbs(min_profit: float = 0.5) -> list[dict]:
    """Get active arbitrage opportunities.

    Args:
        min_profit: Minimum profit percentage

    Returns:
        List of active arb opportunities
    """
    client = get_supabase_client()

    result = (
        client.table("arbitrage_opportunities")
        .select("*")
        .eq("is_active", True)
        .gte("profit_percentage", min_profit)
        .order("profit_percentage", desc=True)
        .limit(20)
        .execute()
    )

    return result.data or []


async def expire_old_arbs() -> int:
    """Mark old arbitrage opportunities as expired.

    Returns:
        Number of arbs expired
    """
    client = get_supabase_client()

    # Expire arbs older than 1 hour
    one_hour_ago = datetime.now(timezone.utc).replace(
        hour=datetime.now(timezone.utc).hour - 1
    ).isoformat()

    result = (
        client.table("arbitrage_opportunities")
        .update({"is_active": False, "expired_at": datetime.now(timezone.utc).isoformat()})
        .eq("is_active", True)
        .lt("detected_at", one_hour_ago)
        .execute()
    )

    return len(result.data) if result.data else 0
