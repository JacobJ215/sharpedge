"""Background job: Scan for +EV betting opportunities.

This job uses two methods for value detection:
1. Model-based: Compares market odds to ML model projections (when available)
2. No-vig consensus: Compares each book's odds to the consensus fair probability

The no-vig method doesn't require ML models and works immediately.
"""

import asyncio
import logging
import os

from sharpedge_agent_pipeline.alerts.alpha_ranker import rank_by_alpha
from sharpedge_analytics import (
    Confidence,
    ValuePlay,
    scan_for_value,
    scan_for_value_no_vig,
)
from sharpedge_analytics.pm_correlation import detect_correlated_positions
from sharpedge_analytics.pm_edge_scanner import scan_pm_edges
from sharpedge_analytics.value_scanner import enrich_with_alpha

from sharpedge_bot.services.odds_service import get_odds_client
from sharpedge_db.client import get_supabase_client
from sharpedge_shared.types import Sport

_fcm_logger = logging.getLogger("sharpedge.jobs.value_scanner.fcm")

_BADGE_THRESHOLDS = [
    (0.85, "PREMIUM"),
    (0.70, "HIGH"),
    (0.50, "MEDIUM"),
    (0.0, "SPECULATIVE"),
]


def _alpha_badge(alpha_score: float) -> str:
    for threshold, badge in _BADGE_THRESHOLDS:
        if alpha_score >= threshold:
            return badge
    return "SPECULATIVE"


def send_fcm_notifications_for_play(play: object) -> int:
    """Send FCM push to all registered devices for a PREMIUM/HIGH alpha play.

    Returns count of notifications sent. Fails silently — never block Discord dispatch.
    """
    # Support both ValuePlay objects (getattr) and plain dicts (.get)
    if isinstance(play, dict):
        alpha_score = float(play.get("alpha_score") or 0.0)
        play_id = str(play.get("id", ""))
        game = play.get("game", "Unknown game")
        bet_type = play.get("bet_type", "")
        ev_pct = float(play.get("ev_percentage") or 0)
        sportsbook = play.get("sportsbook", "")
    else:
        alpha_score = float(getattr(play, "alpha_score", None) or 0.0)
        play_id = str(getattr(play, "id", "") or "")
        game = getattr(play, "game", "Unknown game") or "Unknown game"
        bet_type = getattr(play, "bet_type", "") or ""
        ev_pct = float(getattr(play, "ev_percentage", 0) or 0)
        sportsbook = getattr(play, "sportsbook", "") or ""

    badge = _alpha_badge(alpha_score)
    if badge not in ("PREMIUM", "HIGH"):
        return 0

    # Fetch FCM tokens from Supabase (service_role key bypasses RLS)
    try:
        from supabase import create_client

        supabase_url = os.environ.get("SUPABASE_URL", "")
        service_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not supabase_url or not service_key:
            _fcm_logger.warning("FCM: SUPABASE_URL or SUPABASE_SERVICE_KEY not set — skipping push")
            return 0

        db_client = create_client(supabase_url, service_key)
        result = db_client.table("user_device_tokens").select("fcm_token, platform").execute()
        raw_rows = result.data or []
        tokens: list[str] = []
        for row in raw_rows:
            if not isinstance(row, dict):
                continue
            t = row.get("fcm_token")
            if isinstance(t, str) and t:
                tokens.append(t)
    except Exception as exc:
        _fcm_logger.warning("FCM: failed to fetch device tokens: %s", exc)
        return 0

    if not tokens:
        return 0

    # Build FCM notification payload
    notification_title = f"{badge} Alert: {game}"
    notification_body = f"{bet_type} | EV: {ev_pct:.1f}% | Book: {sportsbook}"
    data_payload = {
        "play_id": play_id,
        "alpha_badge": badge,
        "alpha_score": str(alpha_score),
        "game": game,
    }

    # Send FCM via firebase-admin SDK
    sent_count = 0
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        # Initialize Firebase app once per process
        if not firebase_admin._apps:
            service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
            if service_account_path:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
            else:
                _fcm_logger.warning("FCM: FIREBASE_SERVICE_ACCOUNT_PATH not set — skipping push")
                return 0

        for token in tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=notification_title,
                        body=notification_body,
                    ),
                    data=data_payload,
                    token=token,
                    android=messaging.AndroidConfig(
                        priority="high",
                        notification=messaging.AndroidNotification(
                            channel_id="sharp_alerts",
                            priority="max",
                        ),
                    ),
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(sound="default", badge=1, content_available=True),
                        ),
                    ),
                )
                messaging.send(message)
                sent_count += 1
            except Exception as token_exc:
                _fcm_logger.debug("FCM: failed for token %s...: %s", token[:8], token_exc)

    except ImportError:
        _fcm_logger.warning("FCM: firebase-admin not installed — skipping push notifications")
    except Exception as exc:
        _fcm_logger.warning("FCM: unexpected error: %s", exc)

    _fcm_logger.info("FCM: sent %d notifications for %s play %s", sent_count, badge, play_id)
    return sent_count


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
    config = getattr(bot, "config", None)
    api_key = (getattr(config, "odds_api_key", "") if config else "") or os.environ.get(
        "ODDS_API_KEY", ""
    )
    redis_url = (getattr(config, "redis_url", "") if config else "") or os.environ.get(
        "REDIS_URL", ""
    )

    sports_to_check = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]
    all_value_plays: list[ValuePlay] = []

    if not api_key:
        logger.warning("Odds API key not configured; skipping sportsbook value scan")
    else:
        odds_client = get_odds_client(api_key, redis_url)
        for sport in sports_to_check:
            try:
                odds_data = await asyncio.to_thread(odds_client.get_odds, sport)
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
                    existing_keys = {
                        (p.game_id, p.sportsbook, p.side) for p in all_value_plays
                    }
                    for play in model_plays:
                        if (play.game_id, play.sportsbook, play.side) not in existing_keys:
                            play.notes = "Model-based projection"
                            all_value_plays.append(play)

            except Exception:
                logger.exception("Error scanning for value in %s", sport)

    # --- PM Scan (Kalshi + Polymarket) ---
    kalshi_api_key = os.environ.get("KALSHI_API_KEY", "")
    polymarket_api_key = os.environ.get("POLYMARKET_API_KEY", None)

    # Fetch active bets once for correlation checks
    try:
        supabase = get_supabase_client()
        bets_result = (
            supabase.table("bets")
            .select("selection,game,sport,sportsbook")
            .in_("result", ["PENDING"])
            .execute()
        )
        active_bets_for_correlation = bets_result.data or []
    except Exception:
        logger.warning(
            "Failed to fetch active bets for correlation check; skipping correlation warnings"
        )
        active_bets_for_correlation = []

    # Kalshi scan
    kalshi_private_key = os.environ.get("KALSHI_PRIVATE_KEY", "") or None
    kalshi_markets: list = []
    if kalshi_api_key:
        try:
            from sharpedge_feeds.kalshi_client import get_kalshi_client

            kalshi_client = await get_kalshi_client(
                kalshi_api_key, private_key_pem=kalshi_private_key
            )
            kalshi_markets = await kalshi_client.get_markets(status="open")
            await kalshi_client.close()
        except Exception:
            logger.warning("Kalshi PM scan failed; continuing")

    # Polymarket scan
    poly_markets: list = []
    try:
        from sharpedge_feeds.polymarket_client import get_polymarket_client

        poly_client = await get_polymarket_client(polymarket_api_key)
        poly_markets = await poly_client.get_markets(active=True)
        await poly_client.close()
    except Exception:
        logger.warning("Polymarket PM scan failed; continuing")

    pm_edges = scan_pm_edges(
        kalshi_markets=kalshi_markets,
        polymarket_markets=poly_markets,
        model_probs={},
        volume_floor=500.0,
    )

    # Insert correlation warnings BEFORE each correlated PM edge
    for edge in pm_edges:
        correlated_bets = detect_correlated_positions(
            pm_market_title=edge.market_title,
            active_bets=active_bets_for_correlation,
            threshold=0.6,
        )
        if correlated_bets:
            _pending_value_alerts.append(
                {
                    "type": "correlation_warning",
                    "pm_market": edge.market_title,
                    "correlated_bets": correlated_bets,
                }
            )
        _pending_value_alerts.append(edge)

    if not all_value_plays:
        return

    # Enrich with alpha scores then rank by alpha (AGENT-05)
    enriched = enrich_with_alpha(all_value_plays)
    ranked_plays = rank_by_alpha(enriched)
    assert all(p.alpha_score is not None for p in ranked_plays[:20] if ranked_plays), (
        "Alpha enrichment incomplete"
    )

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
            client.table("value_plays").insert(
                {
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
                }
            ).execute()
            stored_count += 1

            # Queue alert for high confidence plays
            if play.confidence in [Confidence.HIGH, Confidence.MEDIUM]:
                # FCM FIRST — fires before Discord for PREMIUM/HIGH plays (MOB-04)
                send_fcm_notifications_for_play(play)
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
        result = client.table("projections").select("*").eq("sport", sport).execute()

        projections = []
        for proj in result.data or []:
            projections.append(
                {
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
                }
            )

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
