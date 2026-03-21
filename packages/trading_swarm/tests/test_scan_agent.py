"""Tests for Scan Agent."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sharpedge_trading.agents.scan_agent import (
    _categorize,
    _compute_price_momentum,
    _compute_spread_ratio,
    _is_anomalous,
    _market_to_opportunity,
    _meets_filters,
    scan_once,
)
from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus


def _make_config(**overrides) -> TradingConfig:
    return TradingConfig.from_dict(
        {
            **{
                "confidence_threshold": "0.03",
                "kelly_fraction": "0.25",
                "max_category_exposure": "0.20",
                "max_total_exposure": "0.40",
                "daily_loss_limit": "0.10",
                "min_liquidity": "500",
                "min_edge": "0.03",
            },
            **overrides,
        }
    )


def _future_close_time(hours: float = 24.0) -> str:
    dt = datetime.now(tz=UTC) + timedelta(hours=hours)
    return dt.isoformat()


def _make_market(**overrides) -> dict:
    base = {
        "market_id": "MKT-001",
        "ticker": "TICKER-001",
        "series_ticker": "ECON-CPI",
        "volume": 1000.0,
        "last_price": 45,
        "yes_bid": 44,
        "yes_ask": 46,
        "close_time": _future_close_time(24),
        "baseline_price": 35,  # ~29% momentum (above 15% threshold)
        "baseline_spread": 1,  # spread ratio = 2/1 = 2.0 (at threshold)
        "history_days": 10,
    }
    base.update(overrides)
    return base


# --- Helper function tests ---


def test_categorize_econ():
    assert _categorize("ECON-CPI-2026") == "economic"


def test_categorize_politics():
    assert _categorize("POLITICS-SENATE-2026") == "political"


def test_categorize_crypto():
    assert _categorize("CRYPTO-BTC-2026") == "crypto"


def test_categorize_unknown_defaults_to_economic():
    assert _categorize("UNKNOWN-FOO") == "economic"


def test_compute_price_momentum_detects_spike():
    market = _make_market(last_price=50, baseline_price=35)
    momentum = _compute_price_momentum(market)
    assert momentum > 0.15  # (0.50 - 0.35) / 0.35 ≈ 0.43


def test_compute_spread_ratio_widening():
    market = _make_market(yes_bid=40, yes_ask=50, baseline_spread=2)
    ratio = _compute_spread_ratio(market)
    assert ratio > 2.0


def test_is_anomalous_detects_momentum():
    market = _make_market(last_price=62, baseline_price=45, history_days=10)
    anomalous, momentum, _ = _is_anomalous(market)
    assert anomalous is True
    assert momentum > 0.15


def test_is_anomalous_ignores_new_markets():
    market = _make_market(last_price=62, baseline_price=45, history_days=3)
    anomalous, _, _ = _is_anomalous(market)
    assert anomalous is False


def test_meets_filters_passes_valid_market():
    config = _make_config()
    market = _make_market()
    assert _meets_filters(market, config) is True


def test_meets_filters_rejects_low_liquidity():
    config = _make_config(min_liquidity="1000")
    market = _make_market(volume=100)
    assert _meets_filters(market, config) is False


def test_meets_filters_rejects_too_soon():
    config = _make_config()
    market = _make_market(close_time=_future_close_time(0.5))  # 30 min — below 1h min
    assert _meets_filters(market, config) is False


def test_meets_filters_rejects_too_far():
    config = _make_config()
    market = _make_market(close_time=_future_close_time(24 * 31))  # 31 days — above 30 day max
    assert _meets_filters(market, config) is False


def test_market_to_opportunity_returns_event():
    market = _make_market()
    opp = _market_to_opportunity(market, price_momentum=0.20, spread_ratio=2.5)
    assert opp is not None
    assert opp.market_id == "MKT-001"
    assert opp.category == "economic"
    assert isinstance(opp.time_to_resolution, timedelta)


def test_market_to_opportunity_returns_none_on_bad_data():
    opp = _market_to_opportunity(
        {"volume": 100}, price_momentum=0.0, spread_ratio=1.0
    )  # missing market_id
    assert opp is None


# --- scan_once integration test ---


@pytest.mark.asyncio
async def test_scan_once_emits_opportunity():
    bus = EventBus()
    config = _make_config()

    mock_client = MagicMock()
    mock_client.get_markets.return_value = {"markets": [_make_market()]}

    count = await scan_once(bus, config, mock_client)
    assert count == 1

    opp = await bus.get_opportunity()
    assert opp.market_id == "MKT-001"


@pytest.mark.asyncio
async def test_scan_once_skips_on_api_error():
    bus = EventBus()
    config = _make_config()

    mock_client = MagicMock()
    mock_client.get_markets.side_effect = Exception("Kalshi down")

    count = await scan_once(bus, config, mock_client)
    assert count == 0


@pytest.mark.asyncio
async def test_scan_once_filters_low_liquidity():
    bus = EventBus()
    config = _make_config(min_liquidity="2000")

    mock_client = MagicMock()
    mock_client.get_markets.return_value = {"markets": [_make_market(volume=500)]}

    count = await scan_once(bus, config, mock_client)
    assert count == 0
