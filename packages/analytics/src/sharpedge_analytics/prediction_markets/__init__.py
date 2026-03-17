"""Cross-platform prediction market arbitrage detection.

Backward-compatible re-exports from the prediction_markets sub-package.
All symbols that were importable from `sharpedge_analytics.prediction_markets`
remain importable from the same path.
"""

from .fees import (
    Platform,
    PlatformFees,
    PLATFORM_FEES,
    probability_to_price,
    price_to_probability,
    calculate_fee_adjusted_price,
    _kalshi_fee_formula,
    _kalshi_reduced_fee_formula,
)
from .types import (
    MarketOutcome,
    CanonicalEvent,
)
from .realtime_scanner import (
    RealtimeArbScanner,
    MarketPair,
    LiveArbOpportunity,
    build_scanner_from_matched_markets,
)
from .arbitrage import (
    PredictionMarketArbitrage,
    find_cross_platform_arbitrage,
    _check_arb_direction,
    detect_probability_gap,
    MarketCorrelationNetwork,
    calculate_sizing_instructions,
)

__all__ = [
    # fees
    "Platform",
    "PlatformFees",
    "PLATFORM_FEES",
    "probability_to_price",
    "price_to_probability",
    "calculate_fee_adjusted_price",
    # types
    "MarketOutcome",
    "CanonicalEvent",
    # realtime scanner
    "RealtimeArbScanner",
    "MarketPair",
    "LiveArbOpportunity",
    "build_scanner_from_matched_markets",
    # arbitrage
    "PredictionMarketArbitrage",
    "find_cross_platform_arbitrage",
    "detect_probability_gap",
    "MarketCorrelationNetwork",
    "calculate_sizing_instructions",
]
