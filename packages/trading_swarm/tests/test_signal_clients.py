"""Tests for signal clients — all external calls mocked."""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sharpedge_trading.signals.news_rss_client import _parse_age, _parse_feed, fetch_rss_signals
from sharpedge_trading.signals.reddit_client import fetch_reddit_signals
from sharpedge_trading.signals.twitter_client import fetch_twitter_signals
from sharpedge_trading.signals.types import RawSignal

# --- RawSignal ---

def test_raw_signal_fields():
    sig = RawSignal(source="reddit", text="test headline", age_seconds=60.0, confidence=0.8)
    assert sig.source == "reddit"
    assert sig.text == "test headline"
    assert sig.age_seconds == 60.0
    assert sig.confidence == 0.8


# --- NewsRSSClient ---

_SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Markets rally on strong data</title>
      <pubDate>Mon, 17 Mar 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Fed holds rates steady</title>
      <pubDate>Mon, 17 Mar 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


def test_parse_feed_returns_signals():
    signals = _parse_feed("rss_ap", _SAMPLE_RSS)
    assert len(signals) == 2
    assert signals[0].source == "rss_ap"
    assert signals[0].text == "Markets rally on strong data"
    assert signals[0].confidence == 0.9


def test_parse_feed_returns_empty_on_invalid_xml():
    signals = _parse_feed("rss_ap", "not xml at all <broken")
    assert signals == []


def test_parse_age_returns_float():
    age = _parse_age("Mon, 17 Mar 2026 10:00:00 +0000")
    assert isinstance(age, float)
    assert age >= 0.0


def test_parse_age_returns_zero_on_none():
    assert _parse_age(None) == 0.0


@pytest.mark.asyncio
async def test_fetch_rss_signals_returns_signals():
    mock_response = MagicMock()
    mock_response.text = _SAMPLE_RSS
    mock_response.raise_for_status = MagicMock()

    with patch("sharpedge_trading.signals.news_rss_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        signals = await fetch_rss_signals("inflation")

    assert len(signals) > 0
    assert all(isinstance(s, RawSignal) for s in signals)


@pytest.mark.asyncio
async def test_fetch_rss_signals_returns_empty_on_failure():
    with patch("sharpedge_trading.signals.news_rss_client.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        signals = await fetch_rss_signals("inflation")

    assert signals == []


# --- RedditClient ---

@pytest.mark.asyncio
async def test_reddit_returns_empty_when_no_credentials():
    env = {"REDDIT_CLIENT_ID": "", "REDDIT_CLIENT_SECRET": ""}
    with patch.dict(os.environ, env, clear=False):
        signals = await fetch_reddit_signals("inflation")
    assert signals == []


@pytest.mark.asyncio
async def test_reddit_returns_signals_with_mocked_praw():
    mock_post = MagicMock()
    mock_post.title = "Inflation hits 5-year high"
    mock_post.created_utc = 0.0  # epoch, so age is large but valid

    mock_subreddit = MagicMock()
    mock_subreddit.search.return_value = [mock_post]

    mock_reddit_instance = MagicMock()
    mock_reddit_instance.subreddit.return_value = mock_subreddit

    mock_praw = MagicMock()
    mock_praw.Reddit.return_value = mock_reddit_instance

    env = {"REDDIT_CLIENT_ID": "test-id", "REDDIT_CLIENT_SECRET": "test-secret"}
    with patch.dict(os.environ, env, clear=False):
        with patch.dict("sys.modules", {"praw": mock_praw}):
            signals = await fetch_reddit_signals("inflation")

    assert len(signals) > 0
    assert signals[0].source == "reddit"
    assert signals[0].text == "Inflation hits 5-year high"


# --- TwitterClient ---

@pytest.mark.asyncio
async def test_twitter_returns_empty_when_disabled():
    with patch.dict(os.environ, {"ENABLE_TWITTER_SIGNALS": "false"}):
        signals = await fetch_twitter_signals("inflation")
    assert signals == []


@pytest.mark.asyncio
async def test_twitter_returns_empty_when_no_token():
    env = {"ENABLE_TWITTER_SIGNALS": "true", "TWITTER_BEARER_TOKEN": ""}
    with patch.dict(os.environ, env, clear=False):
        signals = await fetch_twitter_signals("inflation")
    assert signals == []


@pytest.mark.asyncio
async def test_twitter_returns_signals_with_mocked_tweepy():
    mock_tweet = MagicMock()
    mock_tweet.text = "Markets rally on positive jobs data"
    mock_tweet.created_at = None  # no timestamp, age defaults to 0.0

    mock_response = MagicMock()
    mock_response.data = [mock_tweet]

    mock_client_instance = MagicMock()
    mock_client_instance.search_recent_tweets.return_value = mock_response

    mock_tweepy = MagicMock()
    mock_tweepy.Client.return_value = mock_client_instance

    env = {"ENABLE_TWITTER_SIGNALS": "true", "TWITTER_BEARER_TOKEN": "test-token"}
    with patch.dict(os.environ, env, clear=False):
        with patch.dict("sys.modules", {"tweepy": mock_tweepy}):
            signals = await fetch_twitter_signals("markets")

    assert len(signals) > 0
    assert signals[0].source == "twitter"


@pytest.mark.asyncio
async def test_twitter_backoff_on_429():
    """Should retry with backoff on TooManyRequests, then return empty after exhaustion."""

    class FakeTooManyRequests(Exception):
        pass

    mock_client_instance = MagicMock()
    mock_client_instance.search_recent_tweets.side_effect = FakeTooManyRequests("429 Too Many Requests")

    mock_tweepy = MagicMock()
    mock_tweepy.Client.return_value = mock_client_instance
    # Make TooManyRequests detectable by name
    mock_tweepy.errors = MagicMock()
    mock_tweepy.errors.TooManyRequests = FakeTooManyRequests

    env = {"ENABLE_TWITTER_SIGNALS": "true", "TWITTER_BEARER_TOKEN": "test-token"}
    with patch.dict(os.environ, env, clear=False):
        with patch.dict("sys.modules", {"tweepy": mock_tweepy}):
            with patch("sharpedge_trading.signals.twitter_client.asyncio.sleep", new_callable=AsyncMock):
                signals = await fetch_twitter_signals("markets")

    assert signals == []


@pytest.mark.asyncio
async def test_twitter_semaphore_limits_concurrency():
    """Semaphore should be initialized to 5."""
    from sharpedge_trading.signals.twitter_client import _SEMAPHORE
    assert _SEMAPHORE._value == 5
