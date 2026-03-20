"""Fetches AP and Reuters RSS feeds for market-relevant headlines."""
from __future__ import annotations

import asyncio
import logging
import time
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import httpx

from sharpedge_trading.signals.types import RawSignal

logger = logging.getLogger(__name__)

_FEEDS = {
    "rss_bbc": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "rss_nyt": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "rss_wsj": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
}
_TIMEOUT = 10.0
_MAX_AGE_SECONDS = 3600 * 24  # discard items older than 24h


def _parse_age(pub_date: str | None) -> float:
    """Return age in seconds; returns 0 if unparseable (treat as fresh)."""
    if not pub_date:
        return 0.0
    try:
        dt = parsedate_to_datetime(pub_date)
        return max(0.0, time.time() - dt.timestamp())
    except Exception:  # noqa: BLE001
        return 0.0


def _parse_feed(source: str, xml_text: str) -> list[RawSignal]:
    signals: list[RawSignal] = []
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        logger.warning("Failed to parse RSS feed %s: %s", source, exc)
        return signals

    for item in root.iter("item"):
        title_el = item.find("title")
        pub_el = item.find("pubDate")
        if title_el is None or not title_el.text:
            continue
        age = _parse_age(pub_el.text if pub_el is not None else None)
        if age > _MAX_AGE_SECONDS:
            continue
        signals.append(RawSignal(source=source, text=title_el.text.strip(), age_seconds=age, confidence=0.9))
    return signals


async def fetch_rss_signals(query: str) -> list[RawSignal]:
    """Fetch headlines from all RSS feeds. Returns empty list on failure."""
    results: list[RawSignal] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        tasks = [_fetch_one(client, source, url) for source, url in _FEEDS.items()]
        batches = await asyncio.gather(*tasks, return_exceptions=True)
    for batch in batches:
        if isinstance(batch, Exception):
            logger.warning("RSS fetch failed: %s", batch)
            continue
        results.extend(batch)
    return results


async def _fetch_one(client: httpx.AsyncClient, source: str, url: str) -> list[RawSignal]:
    response = await client.get(url)
    response.raise_for_status()
    return _parse_feed(source, response.text)
