"""Prediction Market Feature Assembler — stub for Phase 9 plan 01.

Full implementation in plan 03.
"""

from __future__ import annotations

import numpy as np

# Universal features used across all PM categories.
PM_UNIVERSAL_FEATURES = [
    "market_prob",
    "bid_ask_spread",
    "last_price",
    "volume",
    "open_interest",
    "days_to_close",
]

# Category-specific add-on feature names.
PM_CATEGORY_EXTRA_FEATURES: dict[str, list[str]] = {
    "political": ["polling_average", "election_proximity_days"],
    "economic": ["days_since_last_release", "is_release_imminent"],
    "crypto": ["underlying_asset_price", "price_change_7d"],
    "entertainment": [],
    "weather": [],
}

# Keyword maps for category detection.
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "political": ["election", "vote", "president", "senate", "congress", "ballot"],
    "economic": ["cpi", "inflation", "rate", "gdp", "unemployment", "fed"],
    "crypto": ["bitcoin", "eth", "ethereum", "crypto", "btc", "token"],
    "entertainment": ["oscar", "grammy", "award", "emmy", "golden globe"],
    "weather": ["hurricane", "temperature", "rainfall", "storm", "flood", "tornado"],
}

# Ticker prefix → category mapping.
TICKER_PREFIX_CATEGORY: dict[str, str] = {
    "KXPOL": "political",
    "KXFED": "economic",
    "KXBTC": "crypto",
    "KXETH": "crypto",
}


class PMFeatureAssembler:
    """Assembles feature vectors for prediction market ML models.

    detect_category() is implemented (GREEN).
    assemble() raises NotImplementedError until plan 03.
    """

    def detect_category(self, market: dict) -> str:
        """Classify a market dict into a category string.

        Checks event_ticker prefix first, then question keywords.
        Defaults to 'entertainment' for unrecognised markets.
        """
        ticker: str = market.get("event_ticker", "") or ""
        for prefix, category in TICKER_PREFIX_CATEGORY.items():
            if ticker.upper().startswith(prefix):
                return category

        question: str = (market.get("question", "") or market.get("title", "") or "").lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in question:
                    return category

        return "entertainment"

    def assemble(self, market: dict) -> np.ndarray:
        """Build a numeric feature vector for the market.

        Raises:
            NotImplementedError: until plan 03 implementation.
        """
        raise NotImplementedError("implement in plan 03")
