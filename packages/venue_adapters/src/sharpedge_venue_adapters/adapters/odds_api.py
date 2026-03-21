"""OddsApiAdapter: read-only multi-book sportsbook odds via The Odds API v4."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime

import httpx

from sharpedge_models.no_vig import american_to_implied, devig_shin_n_outcome  # noqa: F401
from sharpedge_venue_adapters.protocol import (
    CanonicalMarket,
    CanonicalOrderBook,
    CanonicalTrade,
    MarketLifecycleState,
    MarketStatePacket,
    SettlementState,
    VenueCapability,
    VenueFeeSchedule,
)

ODDS_API_BASE = "https://api.the-odds-api.com/v4"


class InsufficientCreditsError(Exception):
    """Raised when The Odds API remaining credits fall below threshold."""


class OddsApiAdapter:
    """Read-only sportsbook multi-book line-shopping adapter using The Odds API v4.

    Satisfies VenueAdapter Protocol structurally (runtime_checkable).
    Credit tracking: updates self.remaining_credits from X-Requests-Remaining header.
    Circuit breaker: raises InsufficientCreditsError when credits < 50.
    """

    venue_id: str = "odds_api"
    capabilities: VenueCapability = VenueCapability(
        read_only=True,
        streaming_quotes=False,
        streaming_orderbook=False,
        execution_supported=False,
        maker_rewards=False,
        settlement_feed=False,
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self.remaining_credits: int | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_credits(self) -> None:
        """Raise InsufficientCreditsError if credits are critically low."""
        if self.remaining_credits is not None and self.remaining_credits < 50:
            raise InsufficientCreditsError(
                f"Odds API credits critically low: {self.remaining_credits} remaining. "
                "Pausing to avoid quota exhaustion."
            )

    def _update_credits(self, response: httpx.Response) -> None:
        """Parse X-Requests-Remaining header and store in remaining_credits."""
        remaining = response.headers.get("x-requests-remaining")
        if remaining is not None:
            with contextlib.suppress(ValueError):
                self.remaining_credits = int(remaining)

    def _game_to_canonical(self, game: dict) -> CanonicalMarket:
        """Convert a single Odds API game dict to CanonicalMarket."""
        home_team = game.get("home_team", "")
        away_team = game.get("away_team", "")

        # Collect all h2h implied probs across bookmakers for home team
        home_implied: list[float] = []
        for book in game.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") == "h2h":
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price", 0)
                        if price == 0:
                            continue
                        prob = american_to_implied(int(price))
                        if outcome.get("name") == home_team:
                            home_implied.append(prob)

        yes_bid = min(home_implied) if home_implied else 0.5
        yes_ask = max(home_implied) if home_implied else 0.5

        return CanonicalMarket(
            venue_id="odds_api",
            market_id=game.get("id", ""),
            title=f"{away_team} @ {home_team}",
            state=MarketLifecycleState.OPEN,
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            volume=0,
            close_time_utc=game.get("commence_time", ""),
        )

    # ------------------------------------------------------------------
    # VenueAdapter protocol methods
    # ------------------------------------------------------------------

    async def list_markets(
        self, sport_key: str = "basketball_nba", status: str = "open"
    ) -> list[CanonicalMarket]:
        """Fetch live odds from The Odds API v4 and return CanonicalMarket list."""
        self._check_credits()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{ODDS_API_BASE}/sports/{sport_key}/odds",
                    params={
                        "apiKey": self._api_key,
                        "regions": "us",
                        "markets": "h2h,spreads,totals",
                        "oddsFormat": "american",
                    },
                    timeout=10.0,
                )
                resp.raise_for_status()
                self._update_credits(resp)
                return [self._game_to_canonical(game) for game in resp.json()]
        except (httpx.HTTPError, Exception):
            return []

    async def get_market_details(self, market_id: str) -> CanonicalMarket | None:
        """Return None — The Odds API has no per-market detail endpoint."""
        return None

    async def get_orderbook(self, market_id: str) -> CanonicalOrderBook:
        """Return an empty orderbook — no live orderbook in The Odds API."""
        return CanonicalOrderBook(
            bids=(),
            asks=(),
            timestamp_utc=datetime.now(UTC).isoformat(),
        )

    async def get_trades(self, market_id: str, limit: int = 100) -> list[CanonicalTrade]:
        """Return empty list — The Odds API has no trade feed."""
        return []

    async def get_historical_snapshots(
        self,
        market_id: str,
        start_utc: str = "",
        end_utc: str = "",
    ) -> list[MarketStatePacket]:
        """Return empty list — historical snapshots not available via The Odds API."""
        return []

    async def get_fees_and_limits(self) -> VenueFeeSchedule:
        """Return zero-fee schedule — The Odds API is a data provider, not a venue."""
        return VenueFeeSchedule(
            venue_id="odds_api",
            maker_fee_rate=0.0,
            taker_fee_rate=0.0,
            expected_quote_refresh_seconds=60,
        )

    async def get_settlement_state(self, market_id: str) -> SettlementState | None:
        """Return None — The Odds API has no settlement endpoint."""
        return None


__all__ = ["InsufficientCreditsError", "OddsApiAdapter"]
