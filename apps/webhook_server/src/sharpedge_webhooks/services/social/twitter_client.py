"""Twitter API v2 client for posting tweets and uploading media."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import random
import time
import urllib.parse
from typing import Any

import httpx

logger = logging.getLogger("sharpedge.twitter")

TWITTER_API_V2 = "https://api.twitter.com/2"
TWITTER_UPLOAD_V1 = "https://upload.twitter.com/1.1"


def _pct_encode(value: str) -> str:
    """Percent-encode a string per RFC 3986."""
    return urllib.parse.quote(value, safe="")


def _nonce() -> str:
    return base64.b64encode(random.randbytes(32)).decode().replace("+", "").replace("/", "")[:32]


def _oauth1_header(
    method: str,
    url: str,
    oauth_params: dict[str, str],
    body_params: dict[str, str],
    api_secret: str,
    access_token_secret: str,
) -> str:
    """Build the OAuth 1.0a Authorization header using HMAC-SHA1."""
    # Collect all params for the signature base string
    all_params: dict[str, str] = {**oauth_params, **body_params}
    sorted_pairs = sorted(
        (_pct_encode(k), _pct_encode(v)) for k, v in all_params.items()
    )
    param_string = "&".join(f"{k}={v}" for k, v in sorted_pairs)

    base_string = "&".join(
        [
            method.upper(),
            _pct_encode(url),
            _pct_encode(param_string),
        ]
    )

    signing_key = f"{_pct_encode(api_secret)}&{_pct_encode(access_token_secret)}"
    raw_sig = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    signature = base64.b64encode(raw_sig).decode()

    header_params = {**oauth_params, "oauth_signature": signature}
    header_parts = ", ".join(
        f'{_pct_encode(k)}="{_pct_encode(v)}"'
        for k, v in sorted(header_params.items())
    )
    return f"OAuth {header_parts}"


def _build_oauth_params(api_key: str, access_token: str) -> dict[str, str]:
    return {
        "oauth_consumer_key": api_key,
        "oauth_nonce": _nonce(),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }


async def post_tweet(
    text: str,
    media_id: str | None = None,
    api_key: str | None = None,
    api_secret: str | None = None,
    access_token: str | None = None,
    access_token_secret: str | None = None,
) -> str | None:
    """Post a tweet. Returns tweet_id or None on failure.

    Credentials default to TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET env vars.
    """
    api_key = api_key or os.environ.get("TWITTER_API_KEY", "")
    api_secret = api_secret or os.environ.get("TWITTER_API_SECRET", "")
    access_token = access_token or os.environ.get("TWITTER_ACCESS_TOKEN", "")
    access_token_secret = access_token_secret or os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.warning("post_tweet: missing Twitter credentials, skipping")
        return None

    url = f"{TWITTER_API_V2}/tweets"
    oauth_params = _build_oauth_params(api_key, access_token)
    auth_header = _oauth1_header(
        "POST", url, oauth_params, {}, api_secret, access_token_secret
    )

    payload: dict[str, Any] = {"text": text}
    if media_id:
        payload["media"] = {"media_ids": [media_id]}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code in (200, 201):
            data = resp.json()
            tweet_id = str(data.get("data", {}).get("id", ""))
            if tweet_id:
                logger.info("post_tweet: tweet_id=%s", tweet_id)
                return tweet_id
            logger.warning("post_tweet: no tweet id in response – %s", data)
            return None
        logger.error(
            "post_tweet: HTTP %s – %s", resp.status_code, resp.text[:200]
        )
        return None
    except Exception as exc:
        logger.error("post_tweet: exception – %s", exc)
        return None


async def upload_media(
    image_bytes: bytes,
    media_type: str = "image/png",
    api_key: str | None = None,
    api_secret: str | None = None,
    access_token: str | None = None,
    access_token_secret: str | None = None,
) -> str | None:
    """Upload media to Twitter. Returns media_id string or None on failure.

    Uses the v1.1 media upload endpoint (multipart/form-data).
    """
    api_key = api_key or os.environ.get("TWITTER_API_KEY", "")
    api_secret = api_secret or os.environ.get("TWITTER_API_SECRET", "")
    access_token = access_token or os.environ.get("TWITTER_ACCESS_TOKEN", "")
    access_token_secret = access_token_secret or os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        logger.warning("upload_media: missing Twitter credentials, skipping")
        return None

    url = f"{TWITTER_UPLOAD_V1}/media/upload.json"
    oauth_params = _build_oauth_params(api_key, access_token)
    # Body params for multipart uploads are NOT included in the signature base string
    auth_header = _oauth1_header(
        "POST", url, oauth_params, {}, api_secret, access_token_secret
    )

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={"Authorization": auth_header},
                files={"media": ("media", image_bytes, media_type)},
            )
        if resp.status_code == 200:
            media_id = str(resp.json().get("media_id_string", ""))
            if media_id:
                logger.info("upload_media: media_id=%s", media_id)
                return media_id
            logger.warning("upload_media: no media_id in response – %s", resp.text[:200])
            return None
        logger.error(
            "upload_media: HTTP %s – %s", resp.status_code, resp.text[:200]
        )
        return None
    except Exception as exc:
        logger.error("upload_media: exception – %s", exc)
        return None
