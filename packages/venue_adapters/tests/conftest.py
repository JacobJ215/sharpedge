"""Shared fixtures for venue_adapters tests."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_orderbook():
    """A minimal canonical orderbook fixture for unit tests."""
    return {
        "bids": [{"price": 0.48, "size": 100}, {"price": 0.47, "size": 200}],
        "asks": [{"price": 0.52, "size": 100}, {"price": 0.53, "size": 150}],
        "timestamp_utc": "2026-03-14T12:00:00+00:00",
    }


@pytest.fixture
def mock_market_dict():
    return {
        "venue_id": "kalshi",
        "market_id": "KXBTCD-26MAR14",
        "title": "BTC above $70k on March 14?",
        "status": "open",
        "yes_bid": 0.48,
        "yes_ask": 0.52,
        "volume": 5000,
        "close_time": "2026-03-14T20:00:00+00:00",
    }


@pytest.fixture
def utc_now():
    return datetime.now(timezone.utc)
