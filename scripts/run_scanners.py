"""Standalone scanner — runs value and arbitrage scanning without Discord.

Usage:
    uv run python scripts/run_scanners.py          # run once then loop
    uv run python scripts/run_scanners.py --once   # single pass and exit

Required environment variables:
    SUPABASE_URL        Supabase project URL
    SUPABASE_KEY        Supabase service-role key (or anon key with RLS off)
    ODDS_API_KEY        The Odds API key

Optional:
    REDIS_URL           Redis URL for odds caching (default: no cache)
    SCAN_INTERVAL_MIN   How often to scan in minutes (default: 30)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# ── Path setup (works whether or not packages are pip-installed) ──────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _pkg in ("shared", "database", "odds_client", "analytics"):
    _src = os.path.join(_root, "packages", _pkg, "src")
    if os.path.isdir(_src) and _src not in sys.path:
        sys.path.insert(0, _src)

from sharpedge_analytics import (  # noqa: E402
    scan_for_value_no_vig,
    scan_for_arbitrage,
    rank_value_plays,
    Confidence,
)
from sharpedge_db.client import get_supabase_client  # noqa: E402
from sharpedge_odds.client import OddsClient  # noqa: E402
from sharpedge_shared.types import Sport  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("sharpedge.scanners")

SPORTS = [Sport.NFL, Sport.NBA, Sport.MLB, Sport.NHL]


def _make_odds_client() -> OddsClient:
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY environment variable is required")
    redis_url = os.environ.get("REDIS_URL", "")
    return OddsClient(api_key=api_key, redis_url=redis_url)


# ── Value scanner ─────────────────────────────────────────────────────────

async def run_value_scan(odds_by_sport: dict[str, list]) -> int:
    """Find +EV plays from pre-fetched odds, write new ones to Supabase. Returns stored count."""
    db = get_supabase_client()
    all_plays = []

    for sport, odds_data in odds_by_sport.items():
        try:
            if not odds_data:
                continue
            plays = scan_for_value_no_vig(
                games=odds_data,
                min_ev=1.5,
                min_edge=1.0,
            )
            all_plays.extend(plays)
        except Exception:
            logger.exception("Value scan error for %s", sport)

    if not all_plays:
        logger.info("Value scan: no plays found")
        return 0

    ranked = rank_value_plays(all_plays)

    stored = 0
    for play in ranked[:20]:
        try:
            existing = (
                db.table("value_plays")
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
                continue

            db.table("value_plays").insert({
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
            stored += 1
        except Exception as exc:
            logger.debug("Failed to store value play: %s", exc)

    logger.info("Value scan: %d found, %d new stored", len(all_plays), stored)
    return stored


# ── Arbitrage scanner ─────────────────────────────────────────────────────

def _check_game_arbs(game, sport: str) -> list[dict]:
    """Return arb opportunities for a single game. Accepts Game model or dict."""
    # Support both Pydantic Game objects and raw dicts
    if hasattr(game, "id"):
        game_id = game.id
        home = game.home_team
        away = game.away_team
        bookmakers = game.bookmakers
    else:
        game_id = game.get("id", "")
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        bookmakers = game.get("bookmakers", [])

    game_desc = f"{away} @ {home}"

    spread_home: dict[str, int] = {}
    spread_away: dict[str, int] = {}
    total_over: dict[str, int] = {}
    total_under: dict[str, int] = {}
    ml_home: dict[str, int] = {}
    ml_away: dict[str, int] = {}

    for bm in bookmakers:
        key = bm.key if hasattr(bm, "key") else bm.get("key", "")
        markets = bm.markets if hasattr(bm, "markets") else bm.get("markets", [])
        for mkt in markets:
            mk = mkt.key if hasattr(mkt, "key") else mkt.get("key", "")
            outs = mkt.outcomes if hasattr(mkt, "outcomes") else mkt.get("outcomes", [])
            if mk == "spreads":
                h = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == home), None)
                a = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == away), None)
                if h:
                    spread_home[key] = h.price if hasattr(h, "price") else h.get("price", -110)
                if a:
                    spread_away[key] = a.price if hasattr(a, "price") else a.get("price", -110)
            elif mk == "totals":
                ov = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == "Over"), None)
                un = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == "Under"), None)
                if ov:
                    total_over[key] = ov.price if hasattr(ov, "price") else ov.get("price", -110)
                if un:
                    total_under[key] = un.price if hasattr(un, "price") else un.get("price", -110)
            elif mk == "h2h":
                h = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == home), None)
                a = next((o for o in outs if (o.name if hasattr(o, "name") else o.get("name")) == away), None)
                if h:
                    ml_home[key] = h.price if hasattr(h, "price") else h.get("price", 100)
                if a:
                    ml_away[key] = a.price if hasattr(a, "price") else a.get("price", 100)

    arbs = []
    market_pairs = [
        ("spread", f"{home} spread", f"{away} spread", spread_home, spread_away),
        ("total", "Over", "Under", total_over, total_under),
        ("moneyline", f"{home} ML", f"{away} ML", ml_home, ml_away),
    ]
    for bet_type, label_a, label_b, side_a_odds, side_b_odds in market_pairs:
        if not side_a_odds or not side_b_odds:
            continue
        for result in scan_for_arbitrage(side_a_odds, side_b_odds):
            arbs.append({
                "game_id": game_id,
                "game": game_desc,
                "sport": sport,
                "bet_type": bet_type,
                "book_a": result.book_a,
                "side_a": label_a,
                "odds_a": result.odds_a,
                "stake_a_percentage": result.stake_a_percentage,
                "book_b": result.book_b,
                "side_b": label_b,
                "odds_b": result.odds_b,
                "stake_b_percentage": result.stake_b_percentage,
                "profit_percentage": result.profit_percentage,
                "total_implied": result.total_implied,
            })
    return arbs


async def run_arb_scan(odds_by_sport: dict[str, list]) -> int:
    """Find arbs from pre-fetched odds, write new ones to Supabase. Returns stored count."""
    db = get_supabase_client()
    all_arbs: list[dict] = []

    for sport, odds_data in odds_by_sport.items():
        try:
            if not odds_data:
                continue
            for game in odds_data:
                all_arbs.extend(_check_game_arbs(game, sport))
        except Exception:
            logger.exception("Arb scan error for %s", sport)

    if not all_arbs:
        logger.info("Arb scan: no opportunities found")
        return 0

    all_arbs.sort(key=lambda x: x["profit_percentage"], reverse=True)

    stored = 0
    for arb in all_arbs[:10]:
        try:
            existing = (
                db.table("arbitrage_opportunities")
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

            db.table("arbitrage_opportunities").insert({
                **arb,
                "is_active": True,
            }).execute()
            stored += 1
        except Exception as exc:
            logger.debug("Failed to store arb: %s", exc)

    logger.info("Arb scan: %d found, %d new stored", len(all_arbs), stored)
    return stored


# ── Expiry cleanup ────────────────────────────────────────────────────────

def expire_stale_records() -> None:
    """Mark value plays and arbs older than 2 hours as inactive."""
    db = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()

    try:
        db.table("value_plays").update({"is_active": False}).eq(
            "is_active", True
        ).lt("created_at", now).execute()
    except Exception as exc:
        logger.debug("Expiry cleanup error (value_plays): %s", exc)

    try:
        db.table("arbitrage_opportunities").update({"is_active": False}).eq(
            "is_active", True
        ).lt("detected_at", now).execute()
    except Exception as exc:
        logger.debug("Expiry cleanup error (arbitrage): %s", exc)


# ── Main loop ─────────────────────────────────────────────────────────────

async def fetch_all_odds(odds_client: OddsClient) -> dict[str, list]:
    """Fetch odds for all sports once. Returns dict keyed by sport value."""
    odds_by_sport: dict[str, list] = {}
    loop = asyncio.get_event_loop()
    for sport in SPORTS:
        try:
            # get_odds is synchronous — run in executor to avoid blocking the event loop
            data = await loop.run_in_executor(None, odds_client.get_odds, sport)
            odds_by_sport[sport] = data or []
            logger.debug("Fetched %d games for %s", len(odds_by_sport[sport]), sport)
        except Exception:
            logger.exception("Failed to fetch odds for %s", sport)
            odds_by_sport[sport] = []
    return odds_by_sport


async def scan_once() -> None:
    odds_client = _make_odds_client()
    logger.info("Starting scan pass — %s", datetime.now(timezone.utc).strftime("%H:%M:%S UTC"))

    # Fetch odds once per sport, reuse for both scanners (halves API quota usage)
    odds_by_sport = await fetch_all_odds(odds_client)

    v, a = await asyncio.gather(
        run_value_scan(odds_by_sport),
        run_arb_scan(odds_by_sport),
    )
    logger.info("Pass complete — %d value plays, %d arbs stored", v, a)


async def main_loop(interval_minutes: int) -> None:
    logger.info("Scanner daemon starting (interval=%d min)", interval_minutes)
    while True:
        try:
            await scan_once()
        except Exception:
            logger.exception("Scan pass failed")
        await asyncio.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="SharpEdge standalone scanner")
    parser.add_argument("--once", action="store_true", help="Run one pass and exit")
    args = parser.parse_args()

    interval = int(os.environ.get("SCAN_INTERVAL_MIN", "30"))

    if args.once:
        asyncio.run(scan_once())
    else:
        asyncio.run(main_loop(interval))


if __name__ == "__main__":
    main()
