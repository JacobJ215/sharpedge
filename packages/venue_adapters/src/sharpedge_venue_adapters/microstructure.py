"""Market microstructure models: fill-hazard estimation and spread/depth metrics.

These are closed-form analytical models (no ML), computing in <1ms per call.
Reference: simplified Avellaneda-Stoikov hazard framework for binary event markets.
"""
from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SpreadDepthMetrics:
    """Canonical spread and depth measurements from an orderbook snapshot."""
    spread_prob: float          # ask_prob - bid_prob (in probability units, 0.0–1.0)
    depth_at_best_bid: int      # total size available at best bid price level
    depth_at_best_ask: int      # total size available at best ask price level
    mid_prob: float             # (best_bid + best_ask) / 2


def fill_hazard_estimate(
    limit_price_prob: float,
    best_ask_prob: float,
    depth_at_price: int,
    ttr_hours: float,
    taker_fee_rate: float,
) -> float:
    """Estimate fill probability [0, 1] for a passive limit order.

    Model: exponential decay in distance from best ask, multiplied by
    depth normalization and sigmoid urgency factor.

    Args:
        limit_price_prob: where we want to buy (probability units, 0–1)
        best_ask_prob: current best ask price (probability units, 0–1)
        depth_at_price: contracts available at or better than limit_price
        ttr_hours: time-to-resolution in hours (higher = more time for passive fills)
        taker_fee_rate: e.g. 0.07 for Kalshi (used for net-cost reference only,
                        does NOT affect fill probability directly in this model)

    Returns:
        float: estimated fill probability, capped at 0.95.
    """
    distance = abs(limit_price_prob - best_ask_prob)

    if distance < 1e-6:
        return 0.95  # at-the-market: near-certain fill

    depth_factor = min(1.0, depth_at_price / 100.0)
    # sigmoid: high TTR -> urgency_factor approaches 1.0; low TTR -> approaches 0.5
    urgency_factor = 1.0 / (1.0 + math.exp(-ttr_hours))
    # exponential decay: farther from best ask -> exponentially lower fill prob
    passive_discount = math.exp(-12.0 * distance)

    raw = passive_discount * depth_factor * urgency_factor
    return float(min(0.95, max(0.0, raw)))


def compute_spread_depth(orderbook: dict) -> SpreadDepthMetrics:
    """Extract spread and depth metrics from a canonical orderbook dict.

    Args:
        orderbook: dict with "bids" and "asks" keys, each a list of
                   {"price": float, "size": int} dicts, sorted best-first.

    Returns:
        SpreadDepthMetrics with spread, depth at best levels, and mid.
    """
    bids = orderbook.get("bids", [])
    asks = orderbook.get("asks", [])

    best_bid = float(bids[0]["price"]) if bids else 0.0
    best_ask = float(asks[0]["price"]) if asks else 1.0
    depth_bid = int(bids[0].get("size", 0)) if bids else 0
    depth_ask = int(asks[0].get("size", 0)) if asks else 0

    spread = max(0.0, best_ask - best_bid)
    mid = (best_bid + best_ask) / 2.0

    return SpreadDepthMetrics(
        spread_prob=spread,
        depth_at_best_bid=depth_bid,
        depth_at_best_ask=depth_ask,
        mid_prob=mid,
    )
