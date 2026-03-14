"""Discord posting client using the bot REST API."""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

DISCORD_API = "https://discord.com/api/v10"

logger = logging.getLogger("sharpedge.discord_client")


def _auth_headers(bot_token: str) -> dict[str, str]:
    return {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}


async def post_embed(
    channel_id: str,
    embed: dict,
    bot_token: str | None = None,
) -> str | None:
    """Post an embed to a Discord channel. Returns message_id or None on failure."""
    token = bot_token or os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.error("post_embed: no bot token available")
        return None

    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    payload = {"embeds": [embed]}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(2):
            try:
                resp = await client.post(url, json=payload, headers=_auth_headers(token))
                if resp.status_code == 429 and attempt == 0:
                    logger.warning("post_embed: rate limited, retrying in 2s")
                    await asyncio.sleep(2)
                    continue
                if resp.status_code not in (200, 201):
                    logger.error("post_embed: HTTP %s – %s", resp.status_code, resp.text[:200])
                    return None
                data = resp.json()
                return data.get("id")
            except Exception as exc:
                logger.error("post_embed: exception on attempt %d – %s", attempt, exc)
                return None
    return None


async def edit_embed(
    channel_id: str,
    message_id: str,
    embed: dict,
    bot_token: str | None = None,
) -> bool:
    """Edit an existing embed message (for updating PENDING -> WIN)."""
    token = bot_token or os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.error("edit_embed: no bot token available")
        return False

    url = f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}"
    payload = {"embeds": [embed]}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for attempt in range(2):
            try:
                resp = await client.patch(url, json=payload, headers=_auth_headers(token))
                if resp.status_code == 429 and attempt == 0:
                    logger.warning("edit_embed: rate limited, retrying in 2s")
                    await asyncio.sleep(2)
                    continue
                if resp.status_code != 200:
                    logger.error("edit_embed: HTTP %s – %s", resp.status_code, resp.text[:200])
                    return False
                return True
            except Exception as exc:
                logger.error("edit_embed: exception on attempt %d – %s", attempt, exc)
                return False
    return False


async def post_with_image(
    channel_id: str,
    embed: dict,
    image_bytes: bytes,
    filename: str = "card.png",
    bot_token: str | None = None,
) -> str | None:
    """Post embed with an image attachment. Returns message_id or None."""
    token = bot_token or os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        logger.error("post_with_image: no bot token available")
        return None

    url = f"{DISCORD_API}/channels/{channel_id}/messages"

    import json

    # Discord multipart: 'payload_json' field + file field
    payload_json = json.dumps({"embeds": [embed]})

    auth_header = {"Authorization": f"Bot {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(2):
            try:
                files = {
                    "payload_json": (None, payload_json, "application/json"),
                    "files[0]": (filename, image_bytes, "image/png"),
                }
                resp = await client.post(url, files=files, headers=auth_header)
                if resp.status_code == 429 and attempt == 0:
                    logger.warning("post_with_image: rate limited, retrying in 2s")
                    await asyncio.sleep(2)
                    continue
                if resp.status_code not in (200, 201):
                    logger.error(
                        "post_with_image: HTTP %s – %s", resp.status_code, resp.text[:200]
                    )
                    return None
                data = resp.json()
                return data.get("id")
            except Exception as exc:
                logger.error("post_with_image: exception on attempt %d – %s", attempt, exc)
                return None
    return None
