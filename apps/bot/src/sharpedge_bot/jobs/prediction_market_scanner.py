"""Background job: Cross-platform prediction market arbitrage scanner.

This job scans Kalshi and Polymarket for arbitrage opportunities by:
1. Fetching active markets from both platforms
2. Matching equivalent events using the correlation network
3. Detecting probability gaps exceeding threshold
4. Calculating fee-adjusted profit potential
5. Generating alerts with precise sizing instructions

Peak volume periods (elections, major events) create opportunities
lasting 5-45 seconds, so this scanner runs frequently.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from sharpedge_analytics.prediction_markets import (
    Platform,
    MarketOutcome,
    CanonicalEvent,
    MarketCorrelationNetwork,
    PredictionMarketArbitrage,
    find_cross_platform_arbitrage,
    detect_probability_gap,
    calculate_sizing_instructions,
    PLATFORM_FEES,
)
from sharpedge_db.client import get_supabase_client

logger = logging.getLogger("sharpedge.jobs.pm_scanner")

# Store pending prediction market alerts
_pending_pm_alerts: list[dict] = []

# Correlation network persists across scans
_correlation_network = MarketCorrelationNetwork()


def get_pending_pm_alerts() -> list[dict]:
    """Get and clear pending prediction market alerts."""
    global _pending_pm_alerts
    alerts = _pending_pm_alerts.copy()
    _pending_pm_alerts.clear()
    return alerts


async def scan_prediction_market_arbitrage(bot: object) -> None:
    """Scan for cross-platform prediction market arbitrage.

    This job runs frequently (every 1-2 minutes) to catch
    short-lived opportunities.
    """
    global _pending_pm_alerts, _correlation_network

    config = getattr(bot, "config", None)
    if not config:
        return

    kalshi_key = getattr(config, "kalshi_api_key", None)
    polymarket_key = getattr(config, "polymarket_api_key", None)

    if not kalshi_key:
        logger.debug("Kalshi API key not configured, skipping PM scan")
        return

    try:
        # Import clients
        from sharpedge_feeds.kalshi_client import get_kalshi_client
        from sharpedge_feeds.polymarket_client import get_polymarket_client

        # Fetch markets from both platforms concurrently
        kalshi_client = await get_kalshi_client(kalshi_key)
        polymarket_client = await get_polymarket_client(polymarket_key)

        try:
            kalshi_markets, polymarket_markets = await asyncio.gather(
                kalshi_client.get_markets(status="open", limit=200),
                polymarket_client.get_markets(active=True, limit=200),
            )
        finally:
            await kalshi_client.close()
            await polymarket_client.close()

        # Convert to MarketOutcome and add to correlation network
        for market in kalshi_markets:
            outcome = MarketOutcome(
                platform=Platform.KALSHI,
                market_id=market.ticker,
                outcome_id=market.ticker,
                question=market.title,
                outcome_label="Yes",
                price=market.mid_price,
                volume_24h=market.volume_24h,
                liquidity=float(market.open_interest),
                resolution_source="Kalshi",
                resolution_criteria=market.subtitle,
            )
            _correlation_network.add_market(outcome)

        for market in polymarket_markets:
            outcome = MarketOutcome(
                platform=Platform.POLYMARKET,
                market_id=market.condition_id,
                outcome_id=market.condition_id,
                question=market.question,
                outcome_label="Yes",
                price=market.yes_price,
                volume_24h=market.volume_24h,
                liquidity=market.liquidity,
                resolution_source=market.resolution_source,
                resolution_criteria=market.description[:200] if market.description else "",
            )
            _correlation_network.add_market(outcome)

        # Scan for arbitrage opportunities
        opportunities = _correlation_network.scan_for_arbitrage(
            min_profit_pct=0.5,
            stake=1000.0,
        )

        if not opportunities:
            return

        logger.info("Found %d prediction market arb opportunities", len(opportunities))

        # Store and alert on top opportunities
        client = get_supabase_client()

        for arb in opportunities[:5]:  # Top 5
            try:
                # Store opportunity
                _store_pm_arb(client, arb)

                # Queue alert if profitable enough
                if arb.net_profit_pct >= 1.0:
                    sizing = calculate_sizing_instructions(
                        arb,
                        bankroll=10000.0,
                        max_bet_pct=0.05,
                    )

                    _pending_pm_alerts.append({
                        "type": "prediction_market_arb",
                        "event": arb.canonical_event.description[:100],
                        "profit_pct": arb.net_profit_pct,
                        "sizing": sizing,
                        "platforms": [
                            arb.buy_yes_platform.value,
                            arb.buy_no_platform.value,
                        ],
                        "detected_at": arb.detected_at.isoformat(),
                        "time_sensitive": arb.estimated_window_seconds < 60,
                        "resolution_risk": arb.resolution_risk,
                    })

            except Exception:
                logger.debug("Failed to store PM arb", exc_info=True)

    except Exception:
        logger.exception("Error in prediction market scanner")


def _store_pm_arb(client, arb: PredictionMarketArbitrage) -> None:
    """Store prediction market arbitrage opportunity."""
    try:
        client.table("pm_arbitrage_opportunities").upsert(
            {
                "canonical_event_id": arb.canonical_event.canonical_id,
                "event_description": arb.canonical_event.description[:200],
                "event_type": arb.canonical_event.event_type,
                "buy_yes_platform": arb.buy_yes_platform.value,
                "buy_yes_price": arb.buy_yes_price,
                "buy_no_platform": arb.buy_no_platform.value,
                "buy_no_price": arb.buy_no_price,
                "gross_gap_pct": arb.gross_probability_gap * 100,
                "gross_profit_pct": arb.gross_profit_pct,
                "net_profit_pct": arb.net_profit_pct,
                "stake_yes": arb.stake_yes,
                "stake_no": arb.stake_no,
                "guaranteed_return": arb.guaranteed_return,
                "resolution_risk": arb.resolution_risk,
                "equivalence_confidence": arb.canonical_event.equivalence_confidence,
                "detected_at": arb.detected_at.isoformat(),
                "estimated_window_seconds": arb.estimated_window_seconds,
                "is_active": True,
            },
            on_conflict="canonical_event_id,buy_yes_platform,buy_no_platform",
        ).execute()
    except Exception:
        logger.debug("PM arb storage failed", exc_info=True)


async def quick_scan_probability_gaps(
    kalshi_markets: list[Any],
    polymarket_markets: list[Any],
    threshold_pct: float = 2.0,
) -> list[dict]:
    """Fast scan for probability gaps without full canonicalization.

    This is optimized for speed during high-volume periods.

    Args:
        kalshi_markets: Markets from Kalshi
        polymarket_markets: Markets from Polymarket
        threshold_pct: Minimum gap percentage

    Returns:
        List of gap detections
    """
    gaps = []

    # Build quick lookup by normalized question
    polymarket_lookup: dict[str, Any] = {}
    for pm in polymarket_markets:
        key = _normalize_question(pm.question)
        polymarket_lookup[key] = pm

    for km in kalshi_markets:
        key = _normalize_question(km.title)

        # Try exact match
        pm = polymarket_lookup.get(key)
        if not pm:
            # Try fuzzy match
            pm = _fuzzy_match(key, polymarket_lookup)

        if not pm:
            continue

        # Check probability gap
        gap = detect_probability_gap(
            price_yes_a=km.mid_price,
            price_no_b=1.0 - pm.yes_price,  # NO on Polymarket = 1 - YES
            platform_a=Platform.KALSHI,
            platform_b=Platform.POLYMARKET,
            threshold_pct=threshold_pct,
        )

        if gap:
            gap["kalshi_market"] = km.ticker
            gap["polymarket_market"] = pm.condition_id
            gap["question"] = km.title
            gaps.append(gap)

    return gaps


def _normalize_question(question: str) -> str:
    """Normalize question for matching."""
    # Lowercase, remove punctuation, normalize whitespace
    import re
    normalized = question.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _fuzzy_match(key: str, lookup: dict[str, Any], threshold: float = 0.7) -> Any | None:
    """Find fuzzy match in lookup dictionary."""
    key_words = set(key.split())

    best_match = None
    best_score = 0.0

    for lookup_key, value in lookup.items():
        lookup_words = set(lookup_key.split())

        # Jaccard similarity
        intersection = len(key_words & lookup_words)
        union = len(key_words | lookup_words)
        score = intersection / union if union > 0 else 0

        if score > best_score and score >= threshold:
            best_score = score
            best_match = value

    return best_match


def get_correlation_network() -> MarketCorrelationNetwork:
    """Get the current correlation network for inspection."""
    return _correlation_network


def get_multi_platform_events() -> list[dict]:
    """Get events tracked on multiple platforms."""
    events = _correlation_network.get_multi_platform_events()

    return [
        {
            "canonical_id": e.canonical_id,
            "description": e.description,
            "event_type": e.event_type,
            "platforms": list(e.platform_markets.keys()),
            "platform_count": len(e.platform_markets),
            "equivalence_confidence": e.equivalence_confidence,
            "resolution_risk": e.resolution_risk,
        }
        for e in events
    ]
