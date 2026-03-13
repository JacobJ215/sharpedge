"""Kalshi prediction market API client.

Kalshi is a CFTC-regulated prediction market exchange.
API docs: https://docs.kalshi.com

Authentication:
- RSA-signed requests or API key
- Demo environment for testing
- Rate limits apply
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


@dataclass
class KalshiConfig:
    """Configuration for Kalshi API client."""

    api_key: str
    private_key: str | None = None  # For RSA signing
    environment: str = "prod"  # "demo" or "prod"

    @property
    def base_url(self) -> str:
        if self.environment == "demo":
            return "https://demo-api.kalshi.co"
        return "https://trading-api.kalshi.com"


@dataclass
class KalshiMarket:
    """A Kalshi market/event contract."""

    ticker: str
    event_ticker: str
    title: str
    subtitle: str
    yes_bid: float  # Best bid for YES
    yes_ask: float  # Best ask for YES
    no_bid: float  # Best bid for NO
    no_ask: float  # Best ask for NO
    volume: int
    volume_24h: int
    open_interest: int
    last_price: float
    status: str  # "open", "closed", "settled"
    close_time: datetime | None
    result: str | None  # "yes", "no", None if unsettled

    @property
    def mid_price(self) -> float:
        """Mid-market price for YES."""
        return (self.yes_bid + self.yes_ask) / 2

    @property
    def implied_probability(self) -> float:
        """Implied probability based on mid price."""
        return self.mid_price

    @property
    def spread(self) -> float:
        """Bid-ask spread."""
        return self.yes_ask - self.yes_bid


class KalshiClient:
    """Client for Kalshi prediction market API."""

    def __init__(self, config: KalshiConfig):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=self._build_headers(),
            timeout=30.0,
        )

    def _build_headers(self) -> dict[str, str]:
        """Build authentication headers."""
        timestamp = str(int(time.time() * 1000))

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.config.api_key,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

        # Add signature if private key is provided
        if self.config.private_key:
            signature = self._sign_request(timestamp)
            headers["KALSHI-ACCESS-SIGNATURE"] = signature

        return headers

    def _sign_request(self, timestamp: str, method: str = "GET", path: str = "") -> str:
        """Sign request with RSA key or HMAC."""
        message = f"{timestamp}{method}{path}"
        signature = hmac.new(
            self.config.private_key.encode() if self.config.private_key else b"",
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature

    async def get_markets(
        self,
        status: str = "open",
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiMarket]:
        """Get list of markets.

        Args:
            status: Filter by status ("open", "closed", "settled")
            series_ticker: Filter by event series
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            List of KalshiMarket objects
        """
        params = {
            "status": status,
            "limit": limit,
        }
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor

        response = await self._client.get("/trade-api/v2/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for m in data.get("markets", []):
            markets.append(self._parse_market(m))

        return markets

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        """Get a single market by ticker.

        Args:
            ticker: Market ticker (e.g., "KXBTC-25MAR31-T100000")

        Returns:
            KalshiMarket or None if not found
        """
        response = await self._client.get(f"/trade-api/v2/markets/{ticker}")
        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return self._parse_market(data.get("market", {}))

    async def get_orderbook(self, ticker: str) -> dict:
        """Get orderbook for a market.

        Args:
            ticker: Market ticker

        Returns:
            Orderbook with bids and asks
        """
        response = await self._client.get(f"/trade-api/v2/markets/{ticker}/orderbook")
        response.raise_for_status()
        data = response.json()

        return {
            "ticker": ticker,
            "yes_bids": data.get("orderbook", {}).get("yes", []),
            "no_bids": data.get("orderbook", {}).get("no", []),
        }

    async def search_markets(self, query: str, limit: int = 20) -> list[KalshiMarket]:
        """Search markets by keyword.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching markets
        """
        params = {"query": query, "limit": limit}
        response = await self._client.get("/trade-api/v2/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for m in data.get("markets", []):
            markets.append(self._parse_market(m))

        return markets

    async def get_events(self, status: str = "open") -> list[dict]:
        """Get list of events (market groups).

        Args:
            status: Filter by status

        Returns:
            List of event dictionaries
        """
        params = {"status": status}
        response = await self._client.get("/trade-api/v2/events", params=params)
        response.raise_for_status()
        data = response.json()

        return data.get("events", [])

    def _parse_market(self, data: dict) -> KalshiMarket:
        """Parse API response into KalshiMarket."""
        close_time = None
        if data.get("close_time"):
            close_time = datetime.fromisoformat(
                data["close_time"].replace("Z", "+00:00")
            )

        return KalshiMarket(
            ticker=data.get("ticker", ""),
            event_ticker=data.get("event_ticker", ""),
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            yes_bid=data.get("yes_bid", 0) / 100,  # Convert cents to dollars
            yes_ask=data.get("yes_ask", 0) / 100,
            no_bid=data.get("no_bid", 0) / 100,
            no_ask=data.get("no_ask", 0) / 100,
            volume=data.get("volume", 0),
            volume_24h=data.get("volume_24h", 0),
            open_interest=data.get("open_interest", 0),
            last_price=data.get("last_price", 0) / 100,
            status=data.get("status", "unknown"),
            close_time=close_time,
            result=data.get("result"),
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


async def get_kalshi_client(
    api_key: str,
    private_key: str | None = None,
    demo: bool = False,
) -> KalshiClient:
    """Create and return a Kalshi client.

    Args:
        api_key: Kalshi API key
        private_key: RSA private key for signing (optional)
        demo: Use demo environment

    Returns:
        Configured KalshiClient
    """
    config = KalshiConfig(
        api_key=api_key,
        private_key=private_key,
        environment="demo" if demo else "prod",
    )
    return KalshiClient(config)
