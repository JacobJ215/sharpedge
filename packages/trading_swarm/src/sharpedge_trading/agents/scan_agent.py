"""Scan Agent — polls Kalshi every 5 minutes, emits OpportunityEvents."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone


def _kalshi_market_to_dict(market: object) -> dict:
    """Convert a KalshiMarket dataclass to the raw-API dict format scan_agent expects.

    KalshiMarket stores prices as floats [0,1] (already normalized).
    scan_agent helpers expect prices in cents (0-100), so we multiply back by 100.
    close_time in KalshiMarket is a datetime; helpers expect an ISO string.
    """
    close_time_str = None
    ct = getattr(market, "close_time", None)
    if ct is not None:
        close_time_str = ct.isoformat()

    return {
        "market_id": getattr(market, "ticker", ""),
        "ticker": getattr(market, "ticker", ""),
        "series_ticker": getattr(market, "event_ticker", ""),
        "status": getattr(market, "status", "unknown"),
        "yes_bid": int(getattr(market, "yes_bid", 0) * 100),
        "yes_ask": int(getattr(market, "yes_ask", 0) * 100),
        "no_bid": int(getattr(market, "no_bid", 0) * 100),
        "no_ask": int(getattr(market, "no_ask", 0) * 100),
        "last_price": int(getattr(market, "last_price", 0.5) * 100),
        "volume": getattr(market, "volume", 0),
        "volume_24h": getattr(market, "volume_24h", 0),
        "open_interest": getattr(market, "open_interest", 0),
        "order_depth": getattr(market, "order_depth", 0),
        "close_time": close_time_str,
        "result": getattr(market, "result", None),
        # history_days not available from KalshiMarket — default to 0 (anomaly detection disabled for new markets)
        "history_days": getattr(market, "history_days", 0),
        # baseline_price and baseline_spread not in API response — set to None (price = baseline → no momentum)
        "baseline_price": None,
        "baseline_spread": None,
    }

from sharpedge_trading.config import TradingConfig
from sharpedge_trading.events.bus import EventBus
from sharpedge_trading.events.types import OpportunityEvent

logger = logging.getLogger(__name__)

_SCAN_INTERVAL = 900  # 15 minutes
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


def _meets_filters(market: dict, config: TradingConfig) -> tuple[bool, str]:
    """Return (passes, reject_reason) for a market.

    reject_reason is empty string if the market passes all filters.
    """
    # Liquidity filter — prefer order_depth (live order book) over historical volume
    order_depth = float(market.get("order_depth", 0) or 0)
    volume = float(market.get("volume", 0) or 0)
    liquidity = max(order_depth, volume)
    if liquidity < config.min_liquidity:
        return False, f"low_liquidity(depth={order_depth:.0f} vol={volume:.0f} < {config.min_liquidity:.0f})"

    # Time-to-resolution filter
    close_time_str = market.get("close_time") or market.get("expected_expiration_time")
    if not close_time_str:
        return False, "no_close_time"
    try:
        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return False, "bad_close_time_format"
    now = datetime.now(tz=timezone.utc)
    hours_remaining = (close_time - now).total_seconds() / 3600
    if hours_remaining < _MIN_HOURS_TO_RESOLUTION:
        return False, f"expires_too_soon({hours_remaining:.1f}h)"
    if hours_remaining > _MAX_DAYS_TO_RESOLUTION * 24:
        return False, f"expires_too_far({hours_remaining/24:.1f}d)"

    return True, ""


def _is_anomalous(market: dict) -> tuple[bool, float, float]:
    """Return (is_anomalous, price_momentum, spread_ratio).

    New markets (< 7 days of history) are never flagged as anomalous.
    """
    history_days = float(market.get("history_days", 0) or 0)
    price_momentum = _compute_price_momentum(market)
    spread_ratio = _compute_spread_ratio(market)

    if history_days < _MIN_HISTORY_DAYS:
        # No price history available — pass market through to prediction agent for ML scoring
        return True, price_momentum, spread_ratio

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
    not_anomalous_count = 0
    reject_reasons: dict[str, int] = {}

    for market in markets:
        passes, reason = _meets_filters(market, config)
        if not passes:
            bucket = reason.split("(")[0]  # group by reason type, not exact value
            reject_reasons[bucket] = reject_reasons.get(bucket, 0) + 1
            logger.debug(
                "SKIP %s: %s",
                market.get("market_id", "?"),
                reason,
            )
            continue
        filtered_count += 1
        anomalous, price_momentum, spread_ratio = _is_anomalous(market)
        if not anomalous:
            not_anomalous_count += 1
            logger.debug(
                "NO_SIGNAL %s: momentum=%.3f spread_ratio=%.3f",
                market.get("market_id", "?"),
                price_momentum,
                spread_ratio,
            )
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

    reject_summary = ", ".join(f"{k}={v}" for k, v in sorted(reject_reasons.items()))
    logger.info(
        "Scan complete — %d/%d passed pre-filter | %d no_signal | %d opportunities | "
        "total_markets=%d | dropped: [%s]",
        filtered_count,
        len(markets),
        not_anomalous_count,
        emitted,
        len(markets),
        reject_summary or "none",
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
        converted = []
        for item in result:
            if isinstance(item, dict):
                converted.append(item)
            else:
                # KalshiMarket dataclass or similar — convert to expected dict format
                converted.append(_kalshi_market_to_dict(item))
        return converted
    return []


async def run_scan_agent(bus: EventBus, config: TradingConfig, kalshi_client: object) -> None:
    """Main scan agent loop — runs indefinitely, scanning every 5 minutes."""
    logger.info("Scan agent started")
    while True:
        await scan_once(bus, config, kalshi_client)
        await asyncio.sleep(_SCAN_INTERVAL)
