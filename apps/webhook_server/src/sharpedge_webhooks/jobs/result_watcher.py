"""Background job: watches for WIN bets and posts win announcements."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "..",
        "packages",
        "database",
        "src",
    ),
)

from datetime import UTC, datetime, timedelta

from sharpedge_db.client import get_supabase_client
from sharpedge_models.calibration_store import DEFAULT_CALIBRATION_PATH, CalibrationStore

from ..services.social.post_service import post_win_announcement

logger = logging.getLogger("sharpedge.result_watcher")

_WINDOW_HOURS = 24


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _window_start() -> str:
    return (_utc_now() - timedelta(hours=_WINDOW_HOURS)).isoformat()


def _fetch_unannounced_wins(client) -> list[dict]:
    """Return WIN bets settled in last 24h with no existing win_announcement."""
    try:
        resp = (
            client.table("bets")
            .select("*")
            .eq("result", "WIN")
            .gte("settled_at", _window_start())
            .execute()
        )
        all_wins: list[dict] = resp.data or []
    except Exception as exc:
        logger.error("_fetch_unannounced_wins: bets query failed – %s", exc)
        return []

    if not all_wins:
        return []

    # Fetch existing announcements for these bet IDs
    bet_ids = [str(b["id"]) for b in all_wins]
    try:
        ann_resp = (
            client.table("win_announcements").select("bet_id").in_("bet_id", bet_ids).execute()
        )
        announced_ids = {str(row["bet_id"]) for row in (ann_resp.data or [])}
    except Exception as exc:
        logger.warning(
            "_fetch_unannounced_wins: win_announcements query failed – %s; treating all as new",
            exc,
        )
        announced_ids = set()

    return [b for b in all_wins if str(b["id"]) not in announced_ids]


def _fetch_original_alert_post(client, bet_id: str) -> dict | None:
    """Return the social_posts record for the alert linked to this bet, if any."""
    try:
        resp = (
            client.table("social_posts")
            .select("*")
            .eq("source_type", "value_play")
            .eq("source_id", bet_id)
            .eq("platform", "discord")
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("_fetch_original_alert_post: %s", exc)
        return None


def _insert_win_announcement(client, bet_id: str, social_post_ids: list[str]) -> None:
    try:
        client.table("win_announcements").insert(
            {
                "bet_id": bet_id,
                "announced_at": _utc_now().isoformat(),
                "social_post_ids": social_post_ids,
            }
        ).execute()
    except Exception as exc:
        logger.error("_insert_win_announcement: %s", exc)


def _insert_social_posts(client, records: list[dict]) -> list[str]:
    """Insert social_posts rows and return their IDs."""
    inserted_ids: list[str] = []
    for record in records:
        try:
            resp = client.table("social_posts").insert(record).execute()
            rows = resp.data or []
            if rows:
                inserted_ids.append(str(rows[0].get("id", "")))
        except Exception as exc:
            logger.error("_insert_social_posts: %s", exc)
    return inserted_ids


async def trigger_calibration_update(sport: str, resolved_game: dict) -> None:
    """Fetch resolved predictions for sport and update CalibrationStore.

    Pulls predictions made AFTER the current model's trained_at to prevent
    circular calibration (per RESEARCH.md Pitfall 3).
    Falls back to the single resolved_game data point if Supabase is unavailable.
    """
    store = CalibrationStore(DEFAULT_CALIBRATION_PATH)

    probs: list[float] = []
    outcomes: list[bool] = []

    try:
        client = get_supabase_client()
        resp = (
            client.table("backtest_results")
            .select("predicted_probability,outcome")
            .eq("sport", sport)
            .not_.is_("outcome", "null")
            .order("timestamp", desc=True)
            .limit(200)
            .execute()
        )
        rows = resp.data or []
        if rows:
            probs = [float(r["predicted_probability"]) for r in rows]
            outcomes = [bool(r["outcome"]) for r in rows]
    except Exception as exc:
        logger.warning("trigger_calibration_update: Supabase fetch failed (non-fatal): %s", exc)

    # Fall back to resolved_game data point if no rows retrieved
    if not probs:
        prob = resolved_game.get("predicted_probability")
        outcome = resolved_game.get("outcome")
        if prob is not None and outcome is not None:
            probs = [float(prob)]
            outcomes = [bool(outcome)]

    if not probs:
        logger.warning(
            "trigger_calibration_update: no data available for sport=%s, skipping", sport
        )
        return

    try:
        store.update(sport, probs, outcomes)
        logger.info(
            "trigger_calibration_update: sport=%s n=%d confidence_mult=%.3f",
            sport,
            len(probs),
            store.get_confidence_mult(sport),
        )
    except Exception as exc:
        logger.warning("trigger_calibration_update: update failed (non-fatal): %s", exc)


async def run_result_watcher(config: dict, poll_interval: int = 60) -> None:
    """Poll bets table for new WIN results not yet announced. Loop forever."""
    logger.info("result_watcher: starting (poll_interval=%ds)", poll_interval)

    while True:
        try:
            client = get_supabase_client()
            unannounced = _fetch_unannounced_wins(client)

            if unannounced:
                logger.info("result_watcher: %d unannounced WIN(s) found", len(unannounced))

            for bet in unannounced:
                bet_id = str(bet.get("id", ""))
                original_post = _fetch_original_alert_post(client, bet_id)

                # Build a lightweight summary from bet fields
                summary = {
                    "profit": bet.get("profit"),
                    "units_won": bet.get("units"),
                }

                try:
                    records = await post_win_announcement(
                        bet=bet,
                        summary=summary,
                        original_alert_post=original_post,
                        config=config,
                    )
                except Exception as exc:
                    logger.error(
                        "result_watcher: post_win_announcement failed for bet %s – %s",
                        bet_id,
                        exc,
                    )
                    records = []

                post_ids = _insert_social_posts(client, records)
                _insert_win_announcement(client, bet_id, post_ids)
                logger.info(
                    "result_watcher: announced bet %s → %d social post(s)", bet_id, len(records)
                )

                # Trigger calibration update after each WIN bet is stored
                sport = bet.get("sport", "")
                if sport:
                    await trigger_calibration_update(sport, bet)

        except Exception as exc:
            logger.error("result_watcher: cycle error – %s", exc)

        await asyncio.sleep(poll_interval)
