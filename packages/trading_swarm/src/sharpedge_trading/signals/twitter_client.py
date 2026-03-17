"""Twitter/X signal client — feature-flagged via ENABLE_TWITTER_SIGNALS."""
from __future__ import annotations

import logging
import os
import time

from sharpedge_trading.signals.types import RawSignal

logger = logging.getLogger(__name__)

_MAX_RESULTS = 20


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

        return await _fetch_with_tweepy(bearer_token, query)
    except ImportError:
        logger.warning("tweepy not installed — skipping Twitter signals")
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Twitter fetch failed: %s", exc)
        return []


async def _fetch_with_tweepy(bearer_token: str, query: str) -> list[RawSignal]:
    import asyncio
    import tweepy

    client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=False)
    response = await asyncio.get_event_loop().run_in_executor(
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
        signals.append(RawSignal(source="twitter", text=tweet.text, age_seconds=age, confidence=0.6))
    return signals
