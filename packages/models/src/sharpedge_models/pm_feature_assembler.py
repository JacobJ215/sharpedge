"""Prediction Market Feature Assembler.

6-universal + category add-on feature vector for PM binary classifiers.
Used by train_pm_models.py (plan 04) and PMResolutionPredictor (plan 05).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

PM_UNIVERSAL_FEATURES = [
    "market_prob",
    "bid_ask_spread",
    "last_price",
    "volume",
    "open_interest",
    "days_to_close",
]

PM_CATEGORIES = ["political", "economic", "crypto", "entertainment", "weather"]

PM_CATEGORY_EXTRA_FEATURES: dict[str, list[str]] = {
    "political": ["polling_average", "election_proximity_days"],
    "economic": ["days_since_last_release", "is_release_imminent"],
    "crypto": ["underlying_asset_price", "price_change_7d"],
    "entertainment": [],
    "weather": [],
}

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "political": ["election", "vote", "president", "senate", "congress", "ballot", "poll"],
    "economic": ["cpi", "inflation", "rate", "gdp", "unemployment", "fed", "nonfarm"],
    "crypto": ["bitcoin", "eth", "ethereum", "crypto", "btc", "token", "solana", "coinbase"],
    "entertainment": [
        "oscar",
        "grammy",
        "award",
        "emmy",
        "golden globe",
        "box office",
        "film",
        "celebrity",
    ],
    "weather": ["hurricane", "temperature", "rainfall", "storm", "flood", "tornado", "snow"],
}

TICKER_PREFIX_CATEGORY: dict[str, str] = {
    "KXPOL": "political",
    "KXFED": "economic",
    "KXCPI": "economic",
    "KXGDP": "economic",
    "KXNFP": "economic",
    "KXBTC": "crypto",
    "KXETH": "crypto",
    "KXSOL": "crypto",
    "KXENT": "entertainment",
    "KXOSC": "entertainment",
    "KXGRM": "entertainment",
    "KXWTH": "weather",
    "KXHUR": "weather",
}

_COIN_ID_MAP: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


def _extract_coin_id(market: dict) -> str:
    """Parse event_ticker or question for a known coin and return CoinGecko id."""
    ticker = (market.get("event_ticker", "") or "").upper()
    for fragment, coin_id in _COIN_ID_MAP.items():
        if fragment in ticker:
            return coin_id
    question = (market.get("question", "") or "").lower()
    for fragment, coin_id in _COIN_ID_MAP.items():
        if fragment.lower() in question:
            return coin_id
    return "bitcoin"


class PMFeatureAssembler:
    """Assembles feature vectors for prediction market ML models.

    Clients (coingecko, fec, bls) are injected via constructor.
    When None, category add-on features return safe defaults — no network
    calls are made, enabling offline and test usage.
    """

    def __init__(
        self,
        coingecko: Any = None,
        fec: Any = None,
        bls: Any = None,
    ) -> None:
        self._cg = coingecko  # CoinGeckoClient | None
        self._fec = fec  # FECClient | None
        self._bls = bls  # BLSClient | None

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

    def _extract_universal(self, market: dict) -> list[float]:
        """Extract the 6 universal features with try/except fallbacks."""
        features: list[float] = []
        try:
            if "yes_bid" in market and "yes_ask" in market:
                market_prob = (float(market["yes_bid"]) + float(market["yes_ask"])) / 2.0
            else:
                market_prob = float(market.get("market_prob", 0.5))
        except (TypeError, ValueError):
            market_prob = 0.5
        features.append(market_prob)
        try:
            if "yes_bid" in market and "yes_ask" in market:
                spread = float(market["yes_ask"]) - float(market["yes_bid"])
            else:
                spread = float(market.get("bid_ask_spread", 0.0))
        except (TypeError, ValueError):
            spread = 0.0
        features.append(spread)
        for key, default in [("last_price", 0.0), ("volume", 0.0)]:
            try:
                features.append(float(market.get(key, default)))
            except (TypeError, ValueError):
                features.append(default)
        try:
            oi = market.get("open_interest") or market.get("liquidity", 0.0)
            features.append(float(oi))
        except (TypeError, ValueError):
            features.append(0.0)
        try:
            raw = (
                market.get("close_time") or market.get("end_date") or market.get("days_to_close", 0)
            )
            if isinstance(raw, datetime):
                days = max(0, (raw - datetime.now(tz=raw.tzinfo)).days)
            else:
                days = max(0, int(float(raw)))
        except (TypeError, ValueError, AttributeError):
            days = 0
        features.append(float(days))
        return features

    def _extract_category_addons(self, category: str, market: dict) -> list[float]:
        """Extract category-specific add-on features (indices 6–7 when applicable)."""
        if category == "political":
            try:
                polling_avg = (
                    float(self._fec.get_polling_average(market.get("slug", "")))
                    if self._fec
                    else float(market.get("polling_average", 0.0))
                )
            except (TypeError, ValueError, AttributeError):
                polling_avg = 0.0
            try:
                election_days = (
                    float(
                        self._fec.get_election_proximity_days(
                            market.get("election_date", "2099-01-01")
                        )
                    )
                    if self._fec
                    else float(market.get("election_proximity_days", 365))
                )
            except (TypeError, ValueError, AttributeError):
                election_days = 365.0
            return [polling_avg, election_days]
        if category == "economic":
            try:
                days_since = (
                    float(self._bls.get_days_since_last_release("CPI"))
                    if self._bls
                    else float(market.get("days_since_last_release", 30))
                )
            except (TypeError, ValueError, AttributeError):
                days_since = 30.0
            try:
                raw_imminent = (
                    self._bls.get_is_release_imminent("CPI")
                    if self._bls
                    else market.get("is_release_imminent", False)
                )
                imminent = float(int(bool(raw_imminent)))
            except (TypeError, ValueError, AttributeError):
                imminent = 0.0
            return [days_since, imminent]
        if category == "crypto":
            coin_id = _extract_coin_id(market)
            try:
                price = (
                    float(self._cg.get_price(coin_id))
                    if self._cg
                    else float(market.get("underlying_asset_price", 0.0))
                )
            except (TypeError, ValueError, AttributeError):
                price = 0.0
            try:
                change = (
                    float(self._cg.get_price_change_7d(coin_id))
                    if self._cg
                    else float(market.get("price_change_7d", 0.0))
                )
            except (TypeError, ValueError, AttributeError):
                change = 0.0
            return [price, change]
        return []

    def assemble(self, market: dict) -> np.ndarray:
        """Build feature vector: length 6 (entertainment/weather) or 8 (political/economic/crypto).

        Never raises — all field extraction uses try/except fallbacks.
        """
        category = self.detect_category(market)
        universal = self._extract_universal(market)
        addons = self._extract_category_addons(category, market)
        return np.array(universal + addons, dtype=np.float64)
