"""Fetches Reddit posts via PRAW with rate limiting."""
from __future__ import annotations

import asyncio
import logging
import os
import time

from sharpedge_trading.signals.types import RawSignal

logger = logging.getLogger(__name__)

_SEMAPHORE = asyncio.Semaphore(10)
_MAX_POSTS = 10
_SUBREDDITS = ["investing", "politics", "economics", "CryptoCurrency", "stocks"]


async def fetch_reddit_signals(query: str) -> list[RawSignal]:
    """Search Reddit for query-related posts. Returns empty list on failure."""
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "sharpedge-trading-bot/1.0")

    if not client_id or not client_secret:
        logger.warning("REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not set — skipping Reddit signals")
        return []

    try:
        import praw  # deferred — optional dependency

        async with _SEMAPHORE:
            return await asyncio.get_running_loop().run_in_executor(
                None, _fetch_sync, client_id, client_secret, user_agent, query
            )
    except ImportError:
        logger.warning("praw not installed — skipping Reddit signals")
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reddit fetch failed: %s", exc)
        return []


def _fetch_sync(client_id: str, client_secret: str, user_agent: str, query: str) -> list[RawSignal]:
    import praw

    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=user_agent)
    signals: list[RawSignal] = []
    for sub in _SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub)
            for post in subreddit.search(query, limit=_MAX_POSTS // len(_SUBREDDITS) + 1, sort="new"):
                age = max(0.0, time.time() - post.created_utc)
                signals.append(
                    RawSignal(source="reddit", text=post.title, age_seconds=age, confidence=0.6)
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Reddit subreddit %s search failed: %s", sub, exc)
    return signals[:_MAX_POSTS]
