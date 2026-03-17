"""Background job: monitors line movements and writes significant changes to Supabase."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..", "..", "..", "packages", "database", "src",
    ),
)

from sharpedge_db.client import get_supabase_client
from sharpedge_db.queries.odds_history import store_bulk_odds_snapshot, detect_line_movement

logger = logging.getLogger("sharpedge.line_movement_monitor")

_SUPPORTED_SPORTS = ["americanfootball_nfl", "basketball_nba", "baseball_mlb", "icehockey_nhl"]
_ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_active_game_ids(client) -> list[str]:
    """Fallback: pull game_ids from active value_plays not yet started."""
    now_iso = _utc_now().isoformat()
    try:
        resp = (
            client.table("value_plays")
            .select("game_id")
            .eq("is_active", True)
            .gt("game_start_time", now_iso)
            .execute()
        )
        rows = resp.data or []
        return list({r["game_id"] for r in rows if r.get("game_id")})
    except Exception as exc:
        logger.error("line_monitor: value_plays query failed – %s", exc)
        return []


async def _fetch_odds_api(sport: str, api_key: str) -> list[dict]:
    """Fetch current odds from The Odds API for a given sport."""
    try:
        import httpx
        url = f"{_ODDS_API_BASE}/{sport}/odds"
        params = {
            "regions": "us",
            "markets": "spreads,totals,h2h",
            "apiKey": api_key,
        }
        async with httpx.AsyncClient(timeout=30) as hc:
            resp = await hc.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("line_monitor: Odds API %s returned %d", sport, resp.status_code)
        return []
    except Exception as exc:
        logger.error("line_monitor: Odds API fetch failed for %s – %s", sport, exc)
        return []


def _parse_snapshots(events: list[dict]) -> tuple[list[dict], list[str]]:
    """Convert Odds API event list into odds_history snapshot rows and game_ids."""
    snapshots: list[dict] = []
    game_ids: list[str] = []
    now_iso = _utc_now().isoformat()

    for event in events:
        game_id = event.get("id", "")
        if not game_id:
            continue
        game_ids.append(game_id)
        game_start = event.get("commence_time")

        for bookmaker in event.get("bookmakers", []):
            sportsbook = bookmaker.get("key", "")
            for market in bookmaker.get("markets", []):
                bet_type = market.get("key", "")
                for outcome in market.get("outcomes", []):
                    snapshots.append({
                        "game_id": game_id,
                        "sportsbook": sportsbook,
                        "bet_type": bet_type,
                        "line": outcome.get("point"),
                        "odds": outcome.get("price"),
                        "side": outcome.get("name"),
                        "game_start_time": game_start,
                    })

    return snapshots, list(set(game_ids))


def _write_significant_movements(client, movements: list[dict], sport: str) -> None:
    """Persist significant line movements to the line_movements table."""
    records = []
    for m in movements:
        magnitude = abs(m.get("movement", 0.0))
        old_line = m.get("old_line")
        new_line = m.get("new_line")

        # Determine direction
        raw_movement = m.get("movement", 0.0)
        if raw_movement < 0:
            direction = "toward_favorite"
        elif raw_movement > 0:
            direction = "toward_underdog"
        else:
            direction = "unchanged"

        records.append({
            "game_id": m["game_id"],
            "sport": sport,
            "bet_type": m["bet_type"],
            "sportsbook": m.get("sportsbook"),
            "old_line": old_line,
            "new_line": new_line,
            "old_odds": m.get("old_odds"),
            "new_odds": m.get("new_odds"),
            "direction": direction,
            "magnitude": magnitude,
            "is_significant": m.get("is_significant", False),
            "detected_at": _utc_now().isoformat(),
        })

    if not records:
        return

    try:
        client.table("line_movements").insert(records).execute()
        logger.info("line_monitor: inserted %d movement record(s)", len(records))
    except Exception as exc:
        logger.error("line_monitor: failed to write line_movements – %s", exc)


async def run_line_movement_monitor(config: dict, poll_interval: int = 300) -> None:
    """Poll odds sources, store snapshots, detect and record significant line movements."""
    logger.info("line_movement_monitor: starting (poll_interval=%ds)", poll_interval)
    api_key: str = config.get("odds_api_key", "")
    ev_threshold: float = float(config.get("ev_threshold", 1.0))
    sport: str = config.get("sport", "americanfootball_nfl")

    while True:
        try:
            client = get_supabase_client()

            if not api_key:
                logger.warning(
                    "line_monitor: ODDS_API_KEY not set — skipping snapshot fetch; "
                    "set odds_api_key in config to enable live monitoring"
                )
            else:
                events = await _fetch_odds_api(sport, api_key)
                snapshots, game_ids = _parse_snapshots(events)

                if snapshots:
                    inserted = store_bulk_odds_snapshot(snapshots)
                    logger.info(
                        "line_monitor: stored %d snapshot(s) for %d game(s)",
                        inserted, len(game_ids),
                    )
                else:
                    game_ids = _fetch_active_game_ids(client)

                bet_types = ["spreads", "totals", "h2h"]
                for game_id in game_ids:
                    for bet_type in bet_types:
                        try:
                            movements = detect_line_movement(
                                game_id, bet_type, threshold=ev_threshold
                            )
                            significant = [m for m in movements if m.get("is_significant")]
                            if significant:
                                logger.info(
                                    "line_monitor: %d significant movement(s) for game=%s bet_type=%s",
                                    len(significant), game_id, bet_type,
                                )
                                _write_significant_movements(client, significant, sport)
                        except Exception as exc:
                            logger.error(
                                "line_monitor: detect_line_movement failed game=%s bet_type=%s – %s",
                                game_id, bet_type, exc,
                            )

        except Exception as exc:
            logger.error("line_monitor: cycle error – %s", exc)

        await asyncio.sleep(poll_interval)
