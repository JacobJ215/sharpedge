"""CoinGecko API client — Phase 9 plan 02.

Provides synchronous price and 7-day change lookups for cryptocurrency features.
Used by PMFeatureAssembler (plan 03) to enrich prediction market feature vectors.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

_OFFLINE_ENV = "COINGECKO_OFFLINE"


def _is_offline() -> bool:
    return os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")


class CoinGeckoClient:
    """Fetches spot price and 7-day price change from CoinGecko public API.

    Synchronous — designed for training-time feature enrichment.

    Args:
        offline: If True, all methods return 0.0 without network calls.
                 Can also be set via COINGECKO_OFFLINE=true env var.
        api_key: Optional CoinGecko Pro API key (sent as x-cg-pro-api-key header).
    """

    def __init__(self, offline: bool = False, api_key: str | None = None) -> None:
        self._offline = offline or _is_offline()
        self._api_key = api_key or os.environ.get("COINGECKO_API_KEY")
        self._headers: dict[str, str] = {}
        if self._api_key:
            self._headers["x-cg-pro-api-key"] = self._api_key

    def get_price(self, coin_id: str) -> float:
        """Return current USD spot price for coin_id.

        Args:
            coin_id: CoinGecko coin identifier, e.g. "bitcoin", "ethereum".

        Returns:
            Current USD price as float. Returns 0.0 on any error or in offline mode.
        """
        if self._offline:
            return 0.0
        try:
            url = (
                f"{COINGECKO_BASE}/simple/price"
                f"?ids={coin_id}&vs_currencies=usd"
            )
            response = httpx.get(url, headers=self._headers, timeout=5.0)
            data: dict[str, Any] = response.json()
            return float(data[coin_id]["usd"])
        except Exception:
            return 0.0

    def get_price_change_7d(self, coin_id: str) -> float:
        """Return 7-day percentage price change for coin_id.

        Args:
            coin_id: CoinGecko coin identifier, e.g. "bitcoin", "ethereum".

        Returns:
            7-day change as float percentage (positive or negative).
            Returns 0.0 on any error or in offline mode.
        """
        if self._offline:
            return 0.0
        try:
            url = (
                f"{COINGECKO_BASE}/simple/price"
                f"?ids={coin_id}&vs_currencies=usd&price_change_percentage=7d"
            )
            response = httpx.get(url, headers=self._headers, timeout=5.0)
            data: dict[str, Any] = response.json()
            return float(data[coin_id]["usd_7d_change"])
        except Exception:
            return 0.0
