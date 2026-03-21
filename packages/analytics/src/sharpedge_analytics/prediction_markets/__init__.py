"""Cross-platform prediction market arbitrage detection.

Backward-compatible re-exports from the prediction_markets sub-package.
All symbols that were importable from `sharpedge_analytics.prediction_markets`
remain importable from the same path.
"""

from .arbitrage import (
    MarketCorrelationNetwork,
    PredictionMarketArbitrage,
    _check_arb_direction,
    calculate_sizing_instructions,
    detect_probability_gap,
    find_cross_platform_arbitrage,
)
from .fees import (
    PLATFORM_FEES,
    Platform,
    PlatformFees,
    _kalshi_fee_formula,
    _kalshi_reduced_fee_formula,
    calculate_fee_adjusted_price,
    price_to_probability,
    probability_to_price,
)
from .realtime_scanner import (
    LiveArbOpportunity,
    MarketPair,
    RealtimeArbScanner,
    build_scanner_from_matched_markets,
)
from .types import (
    CanonicalEvent,
    MarketOutcome,
)

__all__ = [
    "PLATFORM_FEES",
    "CanonicalEvent",
    "LiveArbOpportunity",
    "MarketCorrelationNetwork",
    # types
    "MarketOutcome",
    "MarketPair",
    # fees
    "Platform",
    "PlatformFees",
    # arbitrage
    "PredictionMarketArbitrage",
    # realtime scanner
    "RealtimeArbScanner",
    "build_scanner_from_matched_markets",
    "calculate_fee_adjusted_price",
    "calculate_sizing_instructions",
    "detect_probability_gap",
    "find_cross_platform_arbitrage",
    "price_to_probability",
    "probability_to_price",
    # backward-compatible private helpers
    "_check_arb_direction",
    "_kalshi_fee_formula",
    "_kalshi_reduced_fee_formula",
]
