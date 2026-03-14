"""Orchestrates posting to Discord, Instagram, and Twitter."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from .discord_client import post_embed, post_with_image
from .instagram_client import post_image_feed, upload_image_to_supabase

logger = logging.getLogger("sharpedge.social")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_record(
    *,
    source_type: str,
    source_id: str,
    platform: str,
    channel_or_handle: str,
    external_post_id: str | None,
    content_text: str,
    image_url: str | None,
    error: str | None,
) -> dict:
    return {
        "source_type": source_type,
        "source_id": source_id,
        "platform": platform,
        "channel_or_handle": channel_or_handle,
        "external_post_id": external_post_id,
        "content_text": content_text,
        "image_url": image_url,
        "posted_at": _now_iso() if external_post_id else None,
        "error": error,
    }


def _build_alert_embed(play: dict) -> dict:
    """Build a Discord embed dict for a value play alert."""
    game = play.get("game", "Unknown Game")
    selection = play.get("selection", "")
    odds = play.get("odds", "")
    ev = play.get("ev_percentage", play.get("ev", ""))
    sport = play.get("sport", "")
    bet_type = play.get("bet_type", "")

    odds_str = f"+{odds}" if isinstance(odds, (int, float)) and odds > 0 else str(odds)
    ev_str = f"{float(ev):.1f}%" if ev != "" else "N/A"

    return {
        "title": f"Value Alert: {game}",
        "description": f"**{selection}** {odds_str}\nEV: {ev_str}",
        "color": 0x00FF88,
        "fields": [
            {"name": "Sport", "value": sport or "N/A", "inline": True},
            {"name": "Type", "value": bet_type or "N/A", "inline": True},
        ],
        "footer": {"text": "SharpEdge | Value Play"},
        "timestamp": _now_iso(),
    }


def _build_win_embed(bet: dict, summary: dict) -> dict:
    """Build a Discord embed dict for a win announcement."""
    game = bet.get("game", "Unknown Game")
    selection = bet.get("selection", "")
    odds = bet.get("odds", "")
    profit = summary.get("profit", bet.get("profit", ""))
    units = summary.get("units_won", bet.get("units", ""))

    odds_str = f"+{odds}" if isinstance(odds, (int, float)) and odds > 0 else str(odds)
    profit_str = f"+{float(profit):.2f}" if profit != "" else "N/A"
    units_str = f"{float(units):.2f}u" if units != "" else "N/A"

    return {
        "title": f"WIN: {game}",
        "description": f"**{selection}** cashed {odds_str}\nProfit: {profit_str} ({units_str})",
        "color": 0xFFD700,
        "footer": {"text": "SharpEdge | Win"},
        "timestamp": _now_iso(),
    }


def _build_alert_caption(play: dict) -> str:
    game = play.get("game", "")
    selection = play.get("selection", "")
    odds = play.get("odds", "")
    ev = play.get("ev_percentage", play.get("ev", ""))
    odds_str = f"+{odds}" if isinstance(odds, (int, float)) and odds > 0 else str(odds)
    ev_str = f"{float(ev):.1f}%" if ev != "" else ""
    parts = [f"Value Alert: {game}", f"{selection} {odds_str}"]
    if ev_str:
        parts.append(f"EV: {ev_str}")
    parts.append("#SharpEdge #ValueBets #SportsBetting")
    return "\n".join(parts)


def _build_win_caption(bet: dict, summary: dict) -> str:
    game = bet.get("game", "")
    selection = bet.get("selection", "")
    odds = bet.get("odds", "")
    profit = summary.get("profit", bet.get("profit", ""))
    odds_str = f"+{odds}" if isinstance(odds, (int, float)) and odds > 0 else str(odds)
    profit_str = f"+{float(profit):.2f}" if profit != "" else ""
    parts = [f"WINNER: {game}", f"{selection} {odds_str} cashed!"]
    if profit_str:
        parts.append(f"Profit: {profit_str}")
    parts.append("#SharpEdge #Winner #SportsBetting")
    return "\n".join(parts)


async def post_alert(play: dict, config: dict) -> list[dict]:
    """Post a value play alert to all enabled platforms.

    config keys: discord_channel_id, discord_bot_token, instagram_account_id,
                 instagram_access_token, supabase_url, supabase_service_key,
                 supabase_storage_bucket, social_image_enabled

    Returns list of social_post records (dicts) ready to insert to DB.
    Each record: {source_type, source_id, platform, channel_or_handle,
                  external_post_id, content_text, image_url, posted_at, error}
    """
    records: list[dict] = []
    play_id = str(play.get("id", ""))
    embed = _build_alert_embed(play)
    caption = _build_alert_caption(play)
    image_public_url: str | None = None

    # Optionally generate and upload image
    social_image_enabled = config.get("social_image_enabled", False)
    if social_image_enabled:
        supabase_url = config.get("supabase_url", os.environ.get("SUPABASE_URL", ""))
        service_key = config.get(
            "supabase_service_key", os.environ.get("SUPABASE_SERVICE_KEY", "")
        )
        bucket = config.get("supabase_storage_bucket", "social-cards")
        if supabase_url and service_key:
            try:
                from .image_generator import generate_alert_card  # type: ignore[import]

                image_bytes = await generate_alert_card(play)
                filename = f"alert_{play_id}.png"
                image_public_url = await upload_image_to_supabase(
                    image_bytes, filename, bucket, supabase_url, service_key
                )
            except Exception as exc:
                logger.warning("post_alert: image generation skipped – %s", exc)

    # Discord
    discord_channel_id = config.get("discord_channel_id", "")
    discord_bot_token = config.get("discord_bot_token", os.environ.get("DISCORD_BOT_TOKEN", ""))
    if discord_channel_id:
        message_id: str | None = None
        error: str | None = None
        try:
            if image_public_url:
                # Attach image as embed thumbnail; post embed only (image already public)
                embed_with_img = dict(embed)
                embed_with_img["thumbnail"] = {"url": image_public_url}
                message_id = await post_embed(
                    discord_channel_id, embed_with_img, bot_token=discord_bot_token
                )
            else:
                message_id = await post_embed(
                    discord_channel_id, embed, bot_token=discord_bot_token
                )
            if message_id:
                logger.info("post_alert: Discord message_id=%s", message_id)
            else:
                error = "Discord post returned no message_id"
                logger.warning("post_alert: %s", error)
        except Exception as exc:
            error = str(exc)
            logger.error("post_alert: Discord exception – %s", exc)

        records.append(
            _make_record(
                source_type="value_play",
                source_id=play_id,
                platform="discord",
                channel_or_handle=discord_channel_id,
                external_post_id=message_id,
                content_text=caption,
                image_url=image_public_url,
                error=error,
            )
        )

    # Instagram
    instagram_account_id = config.get(
        "instagram_account_id", os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    )
    instagram_access_token = config.get(
        "instagram_access_token", os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    )
    if instagram_account_id and instagram_access_token and image_public_url:
        ig_media_id: str | None = None
        ig_error: str | None = None
        try:
            ig_media_id = await post_image_feed(
                image_url=image_public_url,
                caption=caption,
                account_id=instagram_account_id,
                access_token=instagram_access_token,
            )
            if ig_media_id:
                logger.info("post_alert: Instagram media_id=%s", ig_media_id)
            else:
                ig_error = "Instagram post returned no media_id"
                logger.warning("post_alert: %s", ig_error)
        except Exception as exc:
            ig_error = str(exc)
            logger.error("post_alert: Instagram exception – %s", exc)

        records.append(
            _make_record(
                source_type="value_play",
                source_id=play_id,
                platform="instagram",
                channel_or_handle=instagram_account_id,
                external_post_id=ig_media_id,
                content_text=caption,
                image_url=image_public_url,
                error=ig_error,
            )
        )

    return records


async def post_win_announcement(
    bet: dict,
    summary: dict,
    original_alert_post: dict | None,
    config: dict,
) -> list[dict]:
    """Post win announcement to all enabled platforms.

    Returns list of social_post records.
    reply_to_post_id set to original_alert_post['external_post_id'] if available.
    """
    records: list[dict] = []
    bet_id = str(bet.get("id", ""))
    embed = _build_win_embed(bet, summary)
    caption = _build_win_caption(bet, summary)
    image_public_url: str | None = None

    original_external_id: str | None = (
        original_alert_post.get("external_post_id") if original_alert_post else None
    )

    social_image_enabled = config.get("social_image_enabled", False)
    if social_image_enabled:
        supabase_url = config.get("supabase_url", os.environ.get("SUPABASE_URL", ""))
        service_key = config.get(
            "supabase_service_key", os.environ.get("SUPABASE_SERVICE_KEY", "")
        )
        bucket = config.get("supabase_storage_bucket", "social-cards")
        if supabase_url and service_key:
            try:
                from .image_generator import generate_win_card  # type: ignore[import]

                image_bytes = await generate_win_card(bet, summary)
                filename = f"win_{bet_id}.png"
                image_public_url = await upload_image_to_supabase(
                    image_bytes, filename, bucket, supabase_url, service_key
                )
            except Exception as exc:
                logger.warning("post_win_announcement: image generation skipped – %s", exc)

    # Discord
    discord_channel_id = config.get("discord_channel_id", "")
    discord_bot_token = config.get("discord_bot_token", os.environ.get("DISCORD_BOT_TOKEN", ""))
    if discord_channel_id:
        win_embed = dict(embed)
        if original_external_id:
            # Add reference to original alert in footer
            existing_footer = win_embed.get("footer", {})
            win_embed["footer"] = {
                "text": f"{existing_footer.get('text', 'SharpEdge')} | ref:{original_external_id}"
            }
        if image_public_url:
            win_embed["thumbnail"] = {"url": image_public_url}

        message_id: str | None = None
        error: str | None = None
        try:
            message_id = await post_embed(
                discord_channel_id, win_embed, bot_token=discord_bot_token
            )
            if message_id:
                logger.info("post_win_announcement: Discord message_id=%s", message_id)
            else:
                error = "Discord win post returned no message_id"
                logger.warning("post_win_announcement: %s", error)
        except Exception as exc:
            error = str(exc)
            logger.error("post_win_announcement: Discord exception – %s", exc)

        records.append(
            _make_record(
                source_type="bet",
                source_id=bet_id,
                platform="discord",
                channel_or_handle=discord_channel_id,
                external_post_id=message_id,
                content_text=caption,
                image_url=image_public_url,
                error=error,
            )
        )

    # Instagram
    instagram_account_id = config.get(
        "instagram_account_id", os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    )
    instagram_access_token = config.get(
        "instagram_access_token", os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    )
    if instagram_account_id and instagram_access_token and image_public_url:
        ig_media_id: str | None = None
        ig_error: str | None = None
        try:
            ig_media_id = await post_image_feed(
                image_url=image_public_url,
                caption=caption,
                account_id=instagram_account_id,
                access_token=instagram_access_token,
            )
            if ig_media_id:
                logger.info("post_win_announcement: Instagram media_id=%s", ig_media_id)
            else:
                ig_error = "Instagram win post returned no media_id"
                logger.warning("post_win_announcement: %s", ig_error)
        except Exception as exc:
            ig_error = str(exc)
            logger.error("post_win_announcement: Instagram exception – %s", exc)

        records.append(
            _make_record(
                source_type="bet",
                source_id=bet_id,
                platform="instagram",
                channel_or_handle=instagram_account_id,
                external_post_id=ig_media_id,
                content_text=caption,
                image_url=image_public_url,
                error=ig_error,
            )
        )

    return records
