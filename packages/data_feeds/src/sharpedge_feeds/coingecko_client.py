"""CoinGecko API client stub — Phase 9 plan 01.

Full implementation in plan 02.
"""

from __future__ import annotations

import os

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

_OFFLINE_ENV = "COINGECKO_OFFLINE"


class CoinGeckoClient:
    """Fetches spot price and 7-day price change from CoinGecko.

    All methods raise NotImplementedError until plan 02.
    Set COINGECKO_OFFLINE=true to get (0.0, 0.0) defaults without network calls.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._offline = os.environ.get(_OFFLINE_ENV, "").lower() in ("1", "true", "yes")

    def get_price(self, coin_id: str) -> float:
        """Return current USD spot price for coin_id.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")

    def get_price_change_7d(self, coin_id: str) -> float:
        """Return 7-day percentage price change for coin_id.

        Raises:
            NotImplementedError: until plan 02 implementation.
        """
        raise NotImplementedError("implement in plan 02")
