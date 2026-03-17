"""Polymarket prediction market API client.

Polymarket is a decentralized prediction market on Polygon.
API docs: https://docs.polymarket.com

APIs:
- Gamma API: Market discovery & metadata
- CLOB API: Prices, orderbooks & trading
- Data API: Positions, activity & history
- WebSocket: Real-time updates
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


@dataclass
class PolymarketConfig:
    """Configuration for Polymarket API client."""

    api_key: str | None = None
    api_secret: str | None = None
    passphrase: str | None = None

    gamma_url: str = "https://gamma-api.polymarket.com"
    clob_url: str = "https://clob.polymarket.com"
    data_url: str = "https://data-api.polymarket.com"
    timeout: float = 120.0


@dataclass
class PolymarketOutcome:
    """A single outcome in a Polymarket market."""

    token_id: str
    outcome: str  # "Yes" or "No" or custom
    price: float  # 0-1 probability
    winner: bool | None = None


@dataclass
class PolymarketMarket:
    """A Polymarket event/market."""

    condition_id: str
    question_id: str
    question: str
    description: str
    outcomes: list[PolymarketOutcome]
    volume: float
    volume_24h: float
    liquidity: float
    end_date: datetime | None
    resolution_source: str
    active: bool
    closed: bool
    category: str
    slug: str

    @property
    def yes_price(self) -> float:
        """Get YES outcome price."""
        for outcome in self.outcomes:
            if outcome.outcome.lower() == "yes":
                return outcome.price
        return 0.5

    @property
    def no_price(self) -> float:
        """Get NO outcome price."""
        for outcome in self.outcomes:
            if outcome.outcome.lower() == "no":
                return outcome.price
        return 1.0 - self.yes_price

    @property
    def implied_probability(self) -> float:
        """Implied probability of YES."""
        return self.yes_price


class PolymarketClient:
    """Client for Polymarket prediction market APIs."""

    def __init__(self, config: PolymarketConfig):
        self.config = config
        self._gamma_client = httpx.AsyncClient(
            base_url=config.gamma_url,
            timeout=config.timeout,
        )
        self._clob_client = httpx.AsyncClient(
            base_url=config.clob_url,
            headers=self._build_auth_headers() if config.api_key else {},
            timeout=30.0,
        )
        self._data_client = httpx.AsyncClient(
            base_url=config.data_url,
            timeout=30.0,
        )

    def _build_auth_headers(self) -> dict[str, str]:
        """Build authentication headers for CLOB API."""
        if not self.config.api_key:
            return {}

        timestamp = str(int(time.time()))
        headers = {
            "POLY-API-KEY": self.config.api_key,
            "POLY-TIMESTAMP": timestamp,
        }

        if self.config.api_secret:
            # HMAC-SHA256 signature
            message = timestamp
            signature = hmac.new(
                self.config.api_secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["POLY-SIGNATURE"] = signature

        if self.config.passphrase:
            headers["POLY-PASSPHRASE"] = self.config.passphrase

        return headers

    async def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PolymarketMarket]:
        """Get list of markets from Gamma API.

        Args:
            active: Filter for active markets
            closed: Filter for closed markets
            limit: Max results
            offset: Pagination offset

        Returns:
            List of PolymarketMarket objects
        """
        params = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }

        response = await self._gamma_client.get("/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for m in data:
            markets.append(self._parse_market(m))

        return markets

    async def get_market(self, condition_id: str) -> PolymarketMarket | None:
        """Get a single market by condition ID.

        Args:
            condition_id: Market condition ID

        Returns:
            PolymarketMarket or None if not found
        """
        response = await self._gamma_client.get(f"/markets/{condition_id}")
        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return self._parse_market(data)

    async def get_market_by_slug(self, slug: str) -> PolymarketMarket | None:
        """Get market by URL slug.

        Args:
            slug: Market URL slug

        Returns:
            PolymarketMarket or None if not found
        """
        response = await self._gamma_client.get(f"/markets/slug/{slug}")
        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

        return self._parse_market(data)

    async def get_events(self, limit: int = 100) -> list[dict]:
        """Get list of events (multi-market groups).

        Args:
            limit: Max results

        Returns:
            List of event dictionaries
        """
        params = {"limit": limit}
        response = await self._gamma_client.get("/events", params=params)
        response.raise_for_status()

        return response.json()

    async def get_prices(self, token_ids: list[str]) -> dict[str, float]:
        """Get current prices for token IDs from CLOB API.

        Args:
            token_ids: List of outcome token IDs

        Returns:
            Dict mapping token_id to current price
        """
        if not token_ids:
            return {}

        params = {"token_ids": ",".join(token_ids)}
        response = await self._clob_client.get("/prices", params=params)
        response.raise_for_status()
        data = response.json()

        prices = {}
        for token_id, price_data in data.items():
            prices[token_id] = float(price_data.get("price", 0))

        return prices

    async def get_orderbook(self, token_id: str) -> dict:
        """Get orderbook for a token.

        Args:
            token_id: Outcome token ID

        Returns:
            Orderbook with bids and asks
        """
        response = await self._clob_client.get(f"/book?token_id={token_id}")
        response.raise_for_status()
        data = response.json()

        return {
            "token_id": token_id,
            "bids": data.get("bids", []),
            "asks": data.get("asks", []),
            "spread": data.get("spread"),
        }

    async def search_markets(self, query: str, limit: int = 20) -> list[PolymarketMarket]:
        """Search markets by keyword.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of matching markets
        """
        params = {"_q": query, "limit": limit}
        response = await self._gamma_client.get("/markets", params=params)
        response.raise_for_status()
        data = response.json()

        markets = []
        for m in data:
            markets.append(self._parse_market(m))

        return markets

    async def get_market_history(
        self,
        condition_id: str,
        fidelity: int = 60,  # Minutes between data points
    ) -> list[dict]:
        """Get price history for a market.

        Args:
            condition_id: Market condition ID
            fidelity: Resolution in minutes

        Returns:
            List of historical price points
        """
        params = {"fidelity": fidelity}
        response = await self._gamma_client.get(
            f"/markets/{condition_id}/history",
            params=params,
        )
        response.raise_for_status()

        return response.json()

    def _parse_market(self, data: dict) -> PolymarketMarket:
        """Parse API response into PolymarketMarket."""
        outcomes = []
        for token in data.get("tokens", []):
            outcomes.append(PolymarketOutcome(
                token_id=token.get("token_id", ""),
                outcome=token.get("outcome", ""),
                price=float(token.get("price", 0)),
                winner=token.get("winner"),
            ))

        # If no token data, try outcomes array
        if not outcomes:
            for outcome_str in data.get("outcomes", []):
                outcomes.append(PolymarketOutcome(
                    token_id="",
                    outcome=outcome_str,
                    price=0.5,
                ))

        end_date = None
        if data.get("end_date_iso"):
            try:
                end_date = datetime.fromisoformat(
                    data["end_date_iso"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return PolymarketMarket(
            condition_id=data.get("condition_id", ""),
            question_id=data.get("question_id", ""),
            question=data.get("question", ""),
            description=data.get("description", ""),
            outcomes=outcomes,
            volume=float(data.get("volume", 0)),
            volume_24h=float(data.get("volume_num_24hr", 0)),
            liquidity=float(data.get("liquidity", 0)),
            end_date=end_date,
            resolution_source=data.get("resolution_source", ""),
            active=data.get("active", True),
            closed=data.get("closed", False),
            category=data.get("category", ""),
            slug=data.get("slug", ""),
        )

    async def close(self):
        """Close HTTP clients."""
        await self._gamma_client.aclose()
        await self._clob_client.aclose()
        await self._data_client.aclose()


async def get_polymarket_client(
    api_key: str | None = None,
    api_secret: str | None = None,
) -> PolymarketClient:
    """Create and return a Polymarket client.

    Args:
        api_key: Polymarket API key (optional for public endpoints)
        api_secret: API secret for signing (optional)

    Returns:
        Configured PolymarketClient
    """
    config = PolymarketConfig(
        api_key=api_key,
        api_secret=api_secret,
    )
    return PolymarketClient(config)
