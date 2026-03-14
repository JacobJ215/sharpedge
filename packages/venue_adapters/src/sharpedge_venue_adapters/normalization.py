"""Quote normalization: convert raw venue prices to CanonicalQuote.

Supported raw_format values:
- "probability": bid/ask are already 0-1 probability; pass through
- "american":    call american_to_implied() from sharpedge_models.no_vig
- "cents":       divide by 100.0 (Kalshi cents already in kalshi_client._parse_market)
- "decimal":     implied_prob = 1 / decimal_odds
"""
from __future__ import annotations

from sharpedge_models.no_vig import american_to_implied
from sharpedge_venue_adapters.protocol import CanonicalQuote, VenueFeeSchedule


def normalize_to_canonical_quote(
    venue_id: str,
    market_id: str,
    outcome_id: str,
    raw_bid: float,
    raw_ask: float,
    raw_format: str,
    fee_schedule: VenueFeeSchedule,
    timestamp_utc: str,
) -> CanonicalQuote:
    """Convert a raw venue quote to CanonicalQuote with probability-scale prices.

    Args:
        venue_id: Venue identifier (e.g. "kalshi", "polymarket").
        market_id: Market identifier on the venue.
        outcome_id: Outcome identifier (e.g. "yes", "no").
        raw_bid: Bid price in raw_format units.
        raw_ask: Ask price in raw_format units.
        raw_format: One of "probability", "american", "cents", "decimal".
        fee_schedule: VenueFeeSchedule providing maker/taker fee rates.
        timestamp_utc: ISO 8601 UTC timestamp string.

    Returns:
        CanonicalQuote with probability-scale bid/ask and derived mid/spread/fair.

    Raises:
        ValueError: if raw_format is not one of the supported values.
    """
    bid_prob, ask_prob = _to_probability(raw_bid, raw_ask, raw_format)

    mid_prob = (bid_prob + ask_prob) / 2.0
    spread_prob = ask_prob - bid_prob
    # fair_prob = mid for now; devigging is applied separately by the adapter
    fair_prob = mid_prob

    return CanonicalQuote(
        venue_id=venue_id,
        market_id=market_id,
        outcome_id=outcome_id,
        raw_bid=raw_bid,
        raw_ask=raw_ask,
        raw_format=raw_format,
        fair_prob=fair_prob,
        mid_prob=mid_prob,
        spread_prob=spread_prob,
        maker_fee_rate=fee_schedule.maker_fee_rate,
        taker_fee_rate=fee_schedule.taker_fee_rate,
        timestamp_utc=timestamp_utc,
    )


def _to_probability(raw_bid: float, raw_ask: float, raw_format: str) -> tuple[float, float]:
    """Convert raw bid/ask to probability scale."""
    if raw_format == "probability":
        return raw_bid, raw_ask
    elif raw_format == "american":
        bid_prob = american_to_implied(int(raw_bid))
        ask_prob = american_to_implied(int(raw_ask))
        return bid_prob, ask_prob
    elif raw_format == "cents":
        return raw_bid / 100.0, raw_ask / 100.0
    elif raw_format == "decimal":
        # Guard against zero/negative decimals
        bid_prob = 1.0 / raw_bid if raw_bid > 0 else 0.0
        ask_prob = 1.0 / raw_ask if raw_ask > 0 else 0.0
        return bid_prob, ask_prob
    else:
        raise ValueError(
            f"Unsupported raw_format: {raw_format!r}. "
            "Expected one of: 'probability', 'american', 'cents', 'decimal'."
        )


__all__ = ["normalize_to_canonical_quote"]
