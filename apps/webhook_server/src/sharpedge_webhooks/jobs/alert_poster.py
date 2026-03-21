"""Background job: polls value_plays and posts alerts to social platforms."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime

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

from sharpedge_db.client import get_supabase_client

from ..services.social.formatter import format_alert_twitter
from ..services.social.post_service import post_alert
from ..services.social.twitter_client import post_tweet, upload_media

logger = logging.getLogger("sharpedge.alert_poster")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _fetch_new_plays(client, min_ev: float) -> list[dict]:
    """Return active value plays above EV threshold not yet in alert_queue."""
    now_iso = _utc_now().isoformat()
    try:
        resp = (
            client.table("value_plays")
            .select("*")
            .eq("is_active", True)
            .gte("ev_percentage", min_ev)
            .gt("game_start_time", now_iso)
            .execute()
        )
        all_plays: list[dict] = resp.data or []
    except Exception as exc:
        logger.error("_fetch_new_plays: value_plays query failed – %s", exc)
        return []

    if not all_plays:
        return []

    play_ids = [str(p["id"]) for p in all_plays]
    try:
        queued_resp = (
            client.table("alert_queue")
            .select("value_play_id")
            .in_("value_play_id", play_ids)
            .neq("status", "skipped")
            .execute()
        )
        queued_ids = {str(row["value_play_id"]) for row in (queued_resp.data or [])}
    except Exception as exc:
        logger.warning("_fetch_new_plays: alert_queue query failed – %s; treating all as new", exc)
        queued_ids = set()

    return [p for p in all_plays if str(p["id"]) not in queued_ids]


def _insert_alert_queue(client, play_id: str, status: str) -> str | None:
    """Insert a row into alert_queue, return its id."""
    try:
        resp = (
            client.table("alert_queue")
            .insert(
                {"value_play_id": play_id, "status": status, "created_at": _utc_now().isoformat()}
            )
            .execute()
        )
        rows = resp.data or []
        return str(rows[0]["id"]) if rows else None
    except Exception as exc:
        logger.error("_insert_alert_queue: %s", exc)
        return None


def _update_alert_queue(client, queue_id: str, status: str) -> None:
    try:
        client.table("alert_queue").update({"status": status}).eq("id", queue_id).execute()
    except Exception as exc:
        logger.error("_update_alert_queue: %s", exc)


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


async def run_alert_poster(config: dict, poll_interval: int = 60) -> None:
    """Poll value_plays for new high-EV plays not yet queued. Loop forever."""
    logger.info("alert_poster: starting (poll_interval=%ds)", poll_interval)
    min_ev = float(config.get("min_ev_threshold", 3.0))

    while True:
        try:
            client = get_supabase_client()
            new_plays = _fetch_new_plays(client, min_ev)

            if new_plays:
                logger.info("alert_poster: %d new play(s) found", len(new_plays))

            for play in new_plays:
                play_id = str(play.get("id", ""))
                queue_id = _insert_alert_queue(client, play_id, "pending")

                try:
                    records = await post_alert(play, config)
                except Exception as exc:
                    logger.error("alert_poster: post_alert failed for play %s – %s", play_id, exc)
                    records = []

                # Twitter
                twitter_api_key = config.get("twitter_api_key", "")
                twitter_api_secret = config.get("twitter_api_secret", "")
                twitter_access_token = config.get("twitter_access_token", "")
                twitter_access_token_secret = config.get("twitter_access_token_secret", "")

                if twitter_api_key:
                    tweet_text = format_alert_twitter(play)

                    # Retrieve image_bytes from image_public_url if available
                    image_public_url: str | None = next(
                        (r.get("image_url") for r in records if r.get("image_url")), None
                    )
                    media_id: str | None = None
                    if image_public_url and config.get("social_image_enabled"):
                        try:
                            import httpx as _httpx

                            async with _httpx.AsyncClient(timeout=30) as hc:
                                img_resp = await hc.get(image_public_url)
                            if img_resp.status_code == 200:
                                media_id = await upload_media(
                                    img_resp.content,
                                    media_type="image/png",
                                    api_key=twitter_api_key,
                                    api_secret=twitter_api_secret,
                                    access_token=twitter_access_token,
                                    access_token_secret=twitter_access_token_secret,
                                )
                        except Exception as exc:
                            logger.warning("alert_poster: Twitter media upload failed – %s", exc)

                    tweet_id = await post_tweet(
                        tweet_text,
                        media_id=media_id,
                        api_key=twitter_api_key,
                        api_secret=twitter_api_secret,
                        access_token=twitter_access_token,
                        access_token_secret=twitter_access_token_secret,
                    )
                    records.append(
                        {
                            "source_type": "value_play",
                            "source_id": play_id,
                            "platform": "twitter",
                            "channel_or_handle": "",
                            "external_post_id": tweet_id,
                            "content_text": tweet_text,
                            "image_url": image_public_url,
                            "posted_at": _utc_now().isoformat() if tweet_id else None,
                            "error": None if tweet_id else "Twitter post failed",
                        }
                    )

                # Push notification to device subscribers
                if config.get("push_notifications_enabled") and config.get(
                    "firebase_service_account_json"
                ):
                    from ..services.push_service import initialize_firebase, send_push_to_all_users

                    initialize_firebase(config["firebase_service_account_json"])
                    title = f"⚡ Value Alert: {play.get('team', 'Play')} {play.get('market', '')}"
                    ev = float(play.get("ev_percentage", 0))
                    body = f"+{ev:.1f}% EV on {play.get('book', 'book')} — {play.get('game', '')}"
                    push_count = await asyncio.get_event_loop().run_in_executor(
                        None, send_push_to_all_users, title, body, {"play_id": play_id}
                    )
                    logger.info(
                        "alert_poster: sent push to %d device(s) for play %s", push_count, play_id
                    )

                _insert_social_posts(client, records)
                final_status = (
                    "posted" if any(r.get("external_post_id") for r in records) else "failed"
                )
                if queue_id:
                    _update_alert_queue(client, queue_id, final_status)
                logger.info(
                    "alert_poster: play %s → status=%s, %d social post(s)",
                    play_id,
                    final_status,
                    len(records),
                )

        except Exception as exc:
            logger.error("alert_poster: cycle error – %s", exc)

        await asyncio.sleep(poll_interval)
