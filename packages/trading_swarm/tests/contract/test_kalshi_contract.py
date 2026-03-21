"""Contract tests for Kalshi API — verifies response shape matches scan_agent expectations."""

import os

import pytest

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope="module")
def kalshi_client(require_kalshi):
    """Real KalshiClient built from env vars."""
    import sys

    sys.path.insert(0, "packages/data_feeds/src")
    from sharpedge_feeds.kalshi_client import KalshiClient, KalshiConfig

    config = KalshiConfig(
        api_key=os.environ["KALSHI_API_KEY"],
        private_key_pem=os.environ.get("KALSHI_PRIVATE_KEY_PEM"),
        environment=os.environ.get("KALSHI_ENV", "demo"),  # default to demo for safety
    )
    return KalshiClient(config)


async def test_get_markets_returns_list(kalshi_client):
    """Kalshi API returns a non-empty list of markets."""
    markets = await kalshi_client.get_markets(status="open", limit=10)
    assert isinstance(markets, list), "get_markets should return a list"
    assert len(markets) > 0, "Expected at least one open market"


async def test_market_fields_present(kalshi_client):
    """Each KalshiMarket has the fields scan_agent relies on."""
    markets = await kalshi_client.get_markets(status="open", limit=5)
    assert markets, "Need at least one market"
    market = markets[0]
    # These are the fields _kalshi_market_to_dict uses
    assert hasattr(market, "ticker"), "Market must have ticker"
    assert hasattr(market, "yes_bid"), "Market must have yes_bid"
    assert hasattr(market, "yes_ask"), "Market must have yes_ask"
    assert hasattr(market, "last_price"), "Market must have last_price"
    assert hasattr(market, "volume"), "Market must have volume"
    assert hasattr(market, "status"), "Market must have status"


async def test_market_prices_normalized(kalshi_client):
    """KalshiClient normalizes prices to [0, 1] (divided by 100 already)."""
    markets = await kalshi_client.get_markets(status="open", limit=10)
    for m in markets:
        assert 0.0 <= m.yes_bid <= 1.0, f"yes_bid out of range: {m.yes_bid}"
        assert 0.0 <= m.yes_ask <= 1.0, f"yes_ask out of range: {m.yes_ask}"
        assert 0.0 <= m.last_price <= 1.0, f"last_price out of range: {m.last_price}"


async def test_scan_once_runs_without_crash(kalshi_client, require_kalshi):
    """scan_once() survives a real Kalshi API call — no AttributeError on .get()."""
    from sharpedge_trading.agents.scan_agent import scan_once
    from sharpedge_trading.config import TradingConfig
    from sharpedge_trading.events.bus import EventBus

    bus = EventBus()
    config = TradingConfig.defaults()

    # Should not raise — previously crashed because KalshiMarket has no .get()
    emitted = await scan_once(bus, config, kalshi_client)
    assert isinstance(emitted, int), "scan_once should return an int"
    # Don't assert emitted > 0 — depends on market conditions


async def test_get_market_by_ticker(kalshi_client):
    """get_market returns a valid market for a known ticker (or None for unknown)."""
    markets = await kalshi_client.get_markets(status="open", limit=1)
    if not markets:
        pytest.skip("No open markets available")
    ticker = markets[0].ticker
    market = await kalshi_client.get_market(ticker)
    assert market is not None, f"Expected market for ticker {ticker}"
    assert market.ticker == ticker
