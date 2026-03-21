"""Twitter/X signal client — feature-flagged via ENABLE_TWITTER_SIGNALS."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from sharpedge_trading.signals.types import RawSignal

logger = logging.getLogger(__name__)

_SEMAPHORE = asyncio.Semaphore(5)
_MAX_RESULTS = 20
_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0  # seconds


async def fetch_twitter_signals(query: str) -> list[RawSignal]:
    """Fetch Twitter/X signals if ENABLE_TWITTER_SIGNALS=true. Returns empty list otherwise."""
    if os.environ.get("ENABLE_TWITTER_SIGNALS", "false").lower() != "true":
        return []

    bearer_token = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        logger.warning("ENABLE_TWITTER_SIGNALS=true but TWITTER_BEARER_TOKEN not set — skipping")
        return []

    try:
        import tweepy  # deferred — optional dependency

        async with _SEMAPHORE:
            return await _fetch_with_backoff(bearer_token, query, tweepy)
    except ImportError:
        logger.warning("tweepy not installed — skipping Twitter signals")
        return []
    except Exception as exc:
        logger.warning("Twitter fetch failed: %s", exc)
        return []


async def _fetch_with_backoff(bearer_token: str, query: str, tweepy: object) -> list[RawSignal]:
    """Fetch with exponential backoff on 429 responses."""
    for attempt in range(_MAX_RETRIES):
        try:
            return await _fetch_once(bearer_token, query, tweepy)
        except Exception as exc:
            exc_type = type(exc).__name__
            if "TooManyRequests" in exc_type or "429" in str(exc):
                wait = _BACKOFF_BASE**attempt
                logger.warning(
                    "Twitter 429 on attempt %d/%d — backing off %.1fs",
                    attempt + 1,
                    _MAX_RETRIES,
                    wait,
                )
                await asyncio.sleep(wait)
                continue
            raise  # non-429 errors propagate to fetch_twitter_signals
    logger.warning("Twitter fetch exhausted %d retries — returning empty", _MAX_RETRIES)
    return []


async def _fetch_once(bearer_token: str, query: str, tweepy: object) -> list[RawSignal]:
    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=False)  # type: ignore[union-attr]
    response = await asyncio.get_running_loop().run_in_executor(
        None,
        lambda: client.search_recent_tweets(
            query=query,
            max_results=_MAX_RESULTS,
            tweet_fields=["created_at", "public_metrics"],
        ),
    )
    signals: list[RawSignal] = []
    if not response or not response.data:
        return signals
    for tweet in response.data:
        age = 0.0
        if tweet.created_at:
            age = max(0.0, time.time() - tweet.created_at.timestamp())
        signals.append(
            RawSignal(source="twitter", text=tweet.text, age_seconds=age, confidence=0.6)
        )
    return signals
