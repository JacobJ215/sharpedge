"""Instagram Graph API client for feed posts and Reels."""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

GRAPH_API = "https://graph.instagram.com/v21.0"

logger = logging.getLogger("sharpedge.instagram_client")

# Poll intervals for container creation (IG requires async container creation)
_CONTAINER_POLL_INTERVAL = 5  # seconds
_CONTAINER_MAX_POLLS = 12     # up to 60 seconds total


async def _wait_for_container(
    container_id: str,
    account_id: str,
    access_token: str,
    client: httpx.AsyncClient,
) -> bool:
    """Poll container status until FINISHED or error. Returns True on success."""
    url = f"{GRAPH_API}/{container_id}"
    params = {"fields": "status_code", "access_token": access_token}
    for _ in range(_CONTAINER_MAX_POLLS):
        await asyncio.sleep(_CONTAINER_POLL_INTERVAL)
        try:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return False
            status = resp.json().get("status_code", "")
            if status == "FINISHED":
                return True
            if status in ("ERROR", "EXPIRED"):
                logger.error("instagram container %s status: %s", container_id, status)
                return False
        except Exception as exc:
            logger.error("_wait_for_container: %s", exc)
            return False
    logger.error("instagram container %s did not finish in time", container_id)
    return False


async def post_image_feed(
    image_url: str,
    caption: str,
    account_id: str | None = None,
    access_token: str | None = None,
) -> str | None:
    """Post a static image to Instagram feed. Returns IG media_id or None.

    Flow: POST /{account_id}/media (container) -> POST /{account_id}/media_publish
    image_url must be a publicly accessible URL (e.g. Supabase Storage public URL).
    """
    acct = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not acct or not token:
        logger.error("post_image_feed: missing account_id or access_token")
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: create media container
        container_url = f"{GRAPH_API}/{acct}/media"
        container_params = {
            "image_url": image_url,
            "caption": caption,
            "access_token": token,
        }
        try:
            resp = await client.post(container_url, params=container_params)
            if resp.status_code != 200:
                logger.error(
                    "post_image_feed container: HTTP %s – %s", resp.status_code, resp.text[:200]
                )
                return None
            container_id = resp.json().get("id")
            if not container_id:
                logger.error("post_image_feed: no container id in response")
                return None
        except Exception as exc:
            logger.error("post_image_feed container create: %s", exc)
            return None

        # Step 2: wait for container to be ready
        ready = await _wait_for_container(container_id, acct, token, client)
        if not ready:
            return None

        # Step 3: publish
        publish_url = f"{GRAPH_API}/{acct}/media_publish"
        publish_params = {"creation_id": container_id, "access_token": token}
        try:
            resp = await client.post(publish_url, params=publish_params)
            if resp.status_code != 200:
                logger.error(
                    "post_image_feed publish: HTTP %s – %s", resp.status_code, resp.text[:200]
                )
                return None
            media_id = resp.json().get("id")
            logger.info("post_image_feed: published media_id=%s", media_id)
            return media_id
        except Exception as exc:
            logger.error("post_image_feed publish: %s", exc)
            return None


async def post_reel(
    video_url: str,
    caption: str,
    cover_url: str | None = None,
    account_id: str | None = None,
    access_token: str | None = None,
) -> str | None:
    """Post a Reel to Instagram. Returns IG media_id or None.

    Note: video_url must be an MP4 accessible via public URL.
    For image-based Reels (static card), caller should use post_image_feed with
    media_type='REELS' parameter variation.
    """
    acct = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
    token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
    if not acct or not token:
        logger.error("post_reel: missing account_id or access_token")
        return None

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: create Reels container
        container_url = f"{GRAPH_API}/{acct}/media"
        container_params: dict = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": token,
        }
        if cover_url:
            container_params["cover_url"] = cover_url

        try:
            resp = await client.post(container_url, params=container_params)
            if resp.status_code != 200:
                logger.error(
                    "post_reel container: HTTP %s – %s", resp.status_code, resp.text[:200]
                )
                return None
            container_id = resp.json().get("id")
            if not container_id:
                logger.error("post_reel: no container id in response")
                return None
        except Exception as exc:
            logger.error("post_reel container create: %s", exc)
            return None

        # Step 2: wait for video processing
        ready = await _wait_for_container(container_id, acct, token, client)
        if not ready:
            return None

        # Step 3: publish
        publish_url = f"{GRAPH_API}/{acct}/media_publish"
        publish_params = {"creation_id": container_id, "access_token": token}
        try:
            resp = await client.post(publish_url, params=publish_params)
            if resp.status_code != 200:
                logger.error(
                    "post_reel publish: HTTP %s – %s", resp.status_code, resp.text[:200]
                )
                return None
            media_id = resp.json().get("id")
            logger.info("post_reel: published media_id=%s", media_id)
            return media_id
        except Exception as exc:
            logger.error("post_reel publish: %s", exc)
            return None


async def upload_image_to_supabase(
    image_bytes: bytes,
    filename: str,
    bucket: str,
    supabase_url: str,
    service_key: str,
) -> str | None:
    """Upload image bytes to Supabase Storage. Returns public URL or None."""
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "image/png",
        "x-upsert": "true",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(upload_url, content=image_bytes, headers=headers)
            if resp.status_code not in (200, 201):
                logger.error(
                    "upload_image_to_supabase: HTTP %s – %s", resp.status_code, resp.text[:200]
                )
                return None
            public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"
            logger.info("upload_image_to_supabase: uploaded to %s", public_url)
            return public_url
        except Exception as exc:
            logger.error("upload_image_to_supabase: %s", exc)
            return None
