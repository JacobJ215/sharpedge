"""Kalshi prediction market API client.

Kalshi is a CFTC-regulated prediction market exchange.
API docs: https://docs.kalshi.com

Authentication:
- RSA-PSS-SHA256 per-request signing (private key in PEM format)
- KALSHI-ACCESS-KEY: UUID api key
- KALSHI-ACCESS-TIMESTAMP: milliseconds since epoch (refreshed per request)
- KALSHI-ACCESS-SIGNATURE: base64(RSA-PSS-SHA256(timestamp + METHOD + path + body))
"""

import base64
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx


def _rsa_pss_sign(private_key_pem: str, message: str) -> str:
    """Sign a message with RSA-PSS-SHA256 and return base64-encoded result."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
    )
    signature = private_key.sign(
        message.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=hashes.SHA256.digest_size,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


@dataclass
class KalshiConfig:
    """Configuration for Kalshi API client."""

    api_key: str
    private_key_pem: str | None = None  # PEM-encoded RSA private key
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
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    volume: int
    volume_24h: int
    open_interest: int
    last_price: float
    status: str  # "open", "closed", "settled"
    close_time: datetime | None
    result: str | None  # "yes", "no", None if unsettled

    @property
    def mid_price(self) -> float:
        return (self.yes_bid + self.yes_ask) / 2

    @property
    def implied_probability(self) -> float:
        return self.mid_price

    @property
    def spread(self) -> float:
        return self.yes_ask - self.yes_bid


@dataclass
class KalshiOrder:
    """A Kalshi order."""

    order_id: str
    ticker: str
    action: str  # "buy" or "sell"
    side: str  # "yes" or "no"
    type: str  # "limit" or "market"
    count: int
    yes_price: int  # cents (0-99)
    no_price: int   # cents (0-99)
    status: str  # "resting", "canceled", "executed", "pending"
    created_time: datetime | None = None
    expiration_time: datetime | None = None


@dataclass
class KalshiPosition:
    """A position held by the user."""

    ticker: str
    event_ticker: str
    total_cost: int  # cents
    fees_paid: int   # cents
    realized_pnl: int  # cents
    resting_orders_count: int
    position: int  # net YES contracts (negative = net NO)
    market_exposure: int  # cents


class KalshiClient:
    """Client for Kalshi prediction market API.

    Auth headers are generated fresh per-request to avoid stale timestamps.
    """

    def __init__(self, config: KalshiConfig):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

    def _auth_headers(self, method: str, path: str, body: str = "") -> dict[str, str]:
        """Generate fresh auth headers for a single request."""
        timestamp = str(int(time.time() * 1000))
        headers: dict[str, str] = {
            "KALSHI-ACCESS-KEY": self.config.api_key,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
        }

        if self.config.private_key_pem:
            message = f"{timestamp}{method.upper()}{path}{body}"
            headers["KALSHI-ACCESS-SIGNATURE"] = _rsa_pss_sign(
                self.config.private_key_pem, message
            )

        return headers

    # ── Market data (public endpoints) ─────────────────────────────────────

    async def get_markets(
        self,
        status: str = "open",
        series_ticker: str | None = None,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiMarket]:
        """Get list of markets."""
        params: dict[str, Any] = {"status": status, "limit": limit}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor

        path = "/trade-api/v2/markets"
        response = await self._client.get(
            path, params=params, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_market(m) for m in data.get("markets", [])]

    async def get_market(self, ticker: str) -> KalshiMarket | None:
        """Get a single market by ticker."""
        path = f"/trade-api/v2/markets/{ticker}"
        response = await self._client.get(
            path, headers=self._auth_headers("GET", path)
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return self._parse_market(data.get("market", {}))

    async def get_orderbook(self, ticker: str) -> dict:
        """Get orderbook for a market."""
        path = f"/trade-api/v2/markets/{ticker}/orderbook"
        response = await self._client.get(
            path, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        data = response.json()
        return {
            "ticker": ticker,
            "yes_bids": data.get("orderbook", {}).get("yes", []),
            "no_bids": data.get("orderbook", {}).get("no", []),
        }

    async def search_markets(self, query: str, limit: int = 20) -> list[KalshiMarket]:
        """Search markets by keyword."""
        path = "/trade-api/v2/markets"
        params = {"query": query, "limit": limit}
        response = await self._client.get(
            path, params=params, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_market(m) for m in data.get("markets", [])]

    async def get_events(self, status: str = "open") -> list[dict]:
        """Get list of events (market groups)."""
        path = "/trade-api/v2/events"
        params = {"status": status}
        response = await self._client.get(
            path, params=params, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        return response.json().get("events", [])

    # ── Portfolio / authenticated endpoints ────────────────────────────────

    async def get_balance(self) -> dict:
        """Get account balance.

        Returns:
            dict with 'balance' (cents) and 'payout' fields.
        """
        path = "/trade-api/v2/portfolio/balance"
        response = await self._client.get(
            path, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        return response.json()

    async def get_positions(
        self,
        limit: int = 100,
        cursor: str | None = None,
    ) -> list[KalshiPosition]:
        """Get current market positions.

        Args:
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            List of KalshiPosition objects
        """
        path = "/trade-api/v2/portfolio/positions"
        params: dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        response = await self._client.get(
            path, params=params, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        data = response.json()

        positions = []
        for p in data.get("market_positions", []):
            positions.append(KalshiPosition(
                ticker=p.get("ticker", ""),
                event_ticker=p.get("event_ticker", ""),
                total_cost=p.get("total_cost", 0),
                fees_paid=p.get("fees_paid", 0),
                realized_pnl=p.get("realized_pnl", 0),
                resting_orders_count=p.get("resting_orders_count", 0),
                position=p.get("position", 0),
                market_exposure=p.get("market_exposure", 0),
            ))
        return positions

    async def get_open_orders(
        self,
        ticker: str | None = None,
        limit: int = 100,
    ) -> list[KalshiOrder]:
        """Get open/resting orders.

        Args:
            ticker: Filter by market ticker
            limit: Max results

        Returns:
            List of KalshiOrder objects
        """
        path = "/trade-api/v2/portfolio/orders"
        params: dict[str, Any] = {"status": "resting", "limit": limit}
        if ticker:
            params["ticker"] = ticker

        response = await self._client.get(
            path, params=params, headers=self._auth_headers("GET", path)
        )
        response.raise_for_status()
        data = response.json()
        return [self._parse_order(o) for o in data.get("orders", [])]

    async def create_order(
        self,
        ticker: str,
        action: str,
        side: str,
        order_type: str,
        count: int,
        yes_price: int | None = None,
        no_price: int | None = None,
        expiration_ts: int | None = None,
    ) -> KalshiOrder:
        """Place a new order.

        Args:
            ticker: Market ticker (e.g. "KXBTC-25MAR31-T100000")
            action: "buy" or "sell"
            side: "yes" or "no"
            order_type: "limit" or "market"
            count: Number of contracts
            yes_price: YES price in cents (1-99). Required for limit orders.
            no_price: NO price in cents (1-99). Auto-derived if not given.
            expiration_ts: Unix timestamp for GTD orders (None = GTC)

        Returns:
            KalshiOrder with order_id and status
        """
        if order_type == "limit" and yes_price is None and no_price is None:
            raise ValueError("limit orders require yes_price or no_price")

        # Derive the missing price: YES + NO = 100 cents
        if yes_price is not None and no_price is None:
            no_price = 100 - yes_price
        elif no_price is not None and yes_price is None:
            yes_price = 100 - no_price

        payload: dict[str, Any] = {
            "ticker": ticker,
            "action": action,
            "side": side,
            "type": order_type,
            "count": count,
        }
        if yes_price is not None:
            payload["yes_price"] = yes_price
        if no_price is not None:
            payload["no_price"] = no_price
        if expiration_ts is not None:
            payload["expiration_ts"] = expiration_ts

        path = "/trade-api/v2/portfolio/orders"
        body = json.dumps(payload)

        response = await self._client.post(
            path,
            content=body,
            headers={
                **self._auth_headers("POST", path, body),
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return self._parse_order(data.get("order", {}))

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel a resting order.

        Args:
            order_id: Order UUID

        Returns:
            dict with 'order' details and 'reduced_by' count
        """
        path = f"/trade-api/v2/portfolio/orders/{order_id}"
        response = await self._client.delete(
            path, headers=self._auth_headers("DELETE", path)
        )
        response.raise_for_status()
        return response.json()

    # ── Parsing helpers ────────────────────────────────────────────────────

    def _parse_market(self, data: dict) -> KalshiMarket:
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
            yes_bid=data.get("yes_bid", 0) / 100,
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

    def _parse_order(self, data: dict) -> KalshiOrder:
        created_time = None
        if data.get("created_time"):
            try:
                created_time = datetime.fromisoformat(
                    data["created_time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        expiration_time = None
        if data.get("expiration_time"):
            try:
                expiration_time = datetime.fromisoformat(
                    data["expiration_time"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        return KalshiOrder(
            order_id=data.get("order_id", ""),
            ticker=data.get("ticker", ""),
            action=data.get("action", ""),
            side=data.get("side", ""),
            type=data.get("type", ""),
            count=data.get("count", 0),
            yes_price=data.get("yes_price", 0),
            no_price=data.get("no_price", 0),
            status=data.get("status", ""),
            created_time=created_time,
            expiration_time=expiration_time,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


async def get_kalshi_client(
    api_key: str,
    private_key_pem: str | None = None,
    demo: bool = False,
) -> KalshiClient:
    """Create and return a Kalshi client.

    Args:
        api_key: Kalshi API key UUID
        private_key_pem: PEM-encoded RSA private key for request signing.
                         Required for authenticated (trading) endpoints.
        demo: Use demo environment

    Returns:
        Configured KalshiClient
    """
    config = KalshiConfig(
        api_key=api_key,
        private_key_pem=private_key_pem or None,
        environment="demo" if demo else "prod",
    )
    return KalshiClient(config)
