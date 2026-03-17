"""Scan Agent — polls Kalshi every 5 minutes, emits OpportunityEvents."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import OpportunityEvent

logger = logging.getLogger(__name__)

_SCAN_INTERVAL = 300  # 5 minutes
_MIN_HOURS_TO_RESOLUTION = 1.0
_MAX_DAYS_TO_RESOLUTION = 30.0
_PRICE_MOMENTUM_THRESHOLD = 0.15   # 15% momentum spike vs 24h baseline
_SPREAD_WIDENING_THRESHOLD = 2.0   # spread > 2× baseline
_MIN_HISTORY_DAYS = 7              # require 7-day price history before anomaly detection

_MARKET_CATEGORIES = {
    "econ": "economic",
    "politics": "political",
    "crypto": "crypto",
    "sports": "entertainment",
    "entertainment": "entertainment",
    "weather": "weather",
}


def _categorize(series_ticker: str) -> str:
    """Map Kalshi series ticker prefix to internal category."""
    prefix = series_ticker.split("-")[0].lower() if series_ticker else ""
    for key, cat in _MARKET_CATEGORIES.items():
        if key in prefix:
            return cat
    return "economic"  # default


def _compute_spread_ratio(market: dict) -> float:
    """Spread ratio: current_spread / baseline_spread (or 1.0 if no history).

    yes_bid, yes_ask, and baseline_spread are all stored in cents (0–100)
    and normalized to [0, 1] before comparison.
    """
    yes_bid = float(market.get("yes_bid", 0) or 0) / 100
    yes_ask = float(market.get("yes_ask", 0) or 0) / 100
    current_spread = max(0.0, yes_ask - yes_bid)
    # baseline_spread is also stored in cents — normalize to [0, 1]
    raw_baseline = market.get("baseline_spread")
    if raw_baseline is None:
        baseline_spread = current_spread
    else:
        baseline_spread = float(raw_baseline) / 100
    if baseline_spread <= 0:
        return 1.0
    return current_spread / baseline_spread


def _compute_price_momentum(market: dict) -> float:
    """Price momentum: |current_price - baseline_price| / baseline_price."""
    price = float(market.get("last_price", 50) or 50) / 100
    baseline_raw = market.get("baseline_price")
    baseline = float(baseline_raw) / 100 if baseline_raw is not None else price
    if baseline <= 0:
        return 0.0
    return abs(price - baseline) / baseline


def _meets_filters(market: dict, config: TradingConfig) -> bool:
    """Return True if market passes all filters for opportunity consideration."""
    # Liquidity filter
    volume = float(market.get("volume", 0) or 0)
    if volume < config.min_liquidity:
        return False

    # Time-to-resolution filter
    close_time_str = market.get("close_time") or market.get("expected_expiration_time")
    if not close_time_str:
        return False
    try:
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False
    now = datetime.now(tz=timezone.utc)
    hours_remaining = (close_time - now).total_seconds() / 3600
    if hours_remaining < _MIN_HOURS_TO_RESOLUTION or hours_remaining > _MAX_DAYS_TO_RESOLUTION * 24:
        return False

    return True


def _is_anomalous(market: dict) -> tuple[bool, float, float]:
    """Return (is_anomalous, price_momentum, spread_ratio).

    New markets (< 7 days of history) are never flagged as anomalous.
    """
    history_days = float(market.get("history_days", 0) or 0)
    price_momentum = _compute_price_momentum(market)
    spread_ratio = _compute_spread_ratio(market)

    if history_days < _MIN_HISTORY_DAYS:
        return False, price_momentum, spread_ratio

    anomalous = (
        price_momentum > _PRICE_MOMENTUM_THRESHOLD
        or spread_ratio > _SPREAD_WIDENING_THRESHOLD
    )
    return anomalous, price_momentum, spread_ratio


def _market_to_opportunity(market: dict, price_momentum: float, spread_ratio: float) -> OpportunityEvent | None:
    """Convert a Kalshi market dict to an OpportunityEvent. Returns None on parse failure."""
    try:
        close_time_str = market.get("close_time") or market.get("expected_expiration_time", "")
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)
        time_to_resolution = close_time - now

        price_raw = market.get("last_price", 50) or 50
        current_price = float(price_raw) / 100

        return OpportunityEvent(
            market_id=market["market_id"],
            ticker=market.get("ticker", market["market_id"]),
            category=_categorize(market.get("series_ticker", "")),
            current_price=current_price,
            liquidity=float(market.get("volume", 0) or 0),
            time_to_resolution=time_to_resolution,
            price_momentum=price_momentum,
            spread_ratio=spread_ratio,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to parse market %s: %s", market.get("market_id"), exc)
        return None


async def scan_once(bus: EventBus, config: TradingConfig, kalshi_client: object) -> int:
    """Run one scan cycle. Returns number of opportunities emitted."""
    try:
        markets = await _fetch_markets(kalshi_client)
    except Exception as exc:  # noqa: BLE001
        logger.error("Kalshi API error during scan — skipping cycle: %s", exc)
        return 0

    emitted = 0
    filtered_count = 0
    for market in markets:
        if not _meets_filters(market, config):
            continue
        filtered_count += 1
        anomalous, price_momentum, spread_ratio = _is_anomalous(market)
        if not anomalous:
            continue
        opp = _market_to_opportunity(market, price_momentum, spread_ratio)
        if opp is None:
            continue
        await bus.put_opportunity(opp)
        emitted += 1
        logger.info(
            "Opportunity: %s (momentum=%.2f, spread_ratio=%.2f)",
            opp.market_id,
            opp.price_momentum,
            opp.spread_ratio,
        )

    logger.info(
        "Scan complete — %d filtered / %d total → %d opportunities",
        filtered_count,
        len(markets),
        emitted,
    )
    return emitted


async def _fetch_markets(kalshi_client: object) -> list[dict]:
    """Fetch all active markets from Kalshi client.

    Supports:
    - Async clients whose get_markets() is a coroutine (real KalshiClient)
    - Sync clients whose get_markets() returns a dict or list (mocks/test doubles)
    """
    if not hasattr(kalshi_client, "get_markets"):
        logger.warning("Kalshi client has no get_markets method")
        return []

    result = kalshi_client.get_markets()

    # Await if the result is a coroutine (async client)
    if asyncio.iscoroutine(result):
        result = await result

    if isinstance(result, dict):
        return result.get("markets", [])
    if isinstance(result, list):
        return result
    return []


async def run_scan_agent(bus: EventBus, config: TradingConfig, kalshi_client: object) -> None:
    """Main scan agent loop — runs indefinitely, scanning every 5 minutes."""
    logger.info("Scan agent started")
    while True:
        await scan_once(bus, config, kalshi_client)
        await asyncio.sleep(_SCAN_INTERVAL)
