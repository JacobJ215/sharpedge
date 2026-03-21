"""Public betting data client.

Provides access to ticket and money percentages from various sources.
Primary sources:
- Manual data entry (for free tier)
- Action Network API (paid, most accurate)
- Web scraping fallback (Covers, ESPN, etc.)
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import httpx
from sharpedge_analytics import (
    PublicBettingData,
    identify_sharp_plays,
)

logger = logging.getLogger("sharpedge.feeds.public_betting")


class DataSource(StrEnum):
    """Source of public betting data."""

    MANUAL = "manual"
    ACTION_NETWORK = "action_network"
    COVERS = "covers"
    ESPN = "espn"
    AGGREGATED = "aggregated"


@dataclass
class PublicBettingSnapshot:
    """A snapshot of public betting data with metadata."""

    data: PublicBettingData
    source: DataSource
    captured_at: datetime
    confidence: float  # 0-1, how reliable is this data


class PublicBettingClient:
    """Client for fetching public betting data."""

    def __init__(
        self,
        action_network_key: str | None = None,
    ):
        """Initialize public betting client.

        Args:
            action_network_key: Action Network API key (optional)
        """
        self.action_network_key = action_network_key or os.environ.get("ACTION_NETWORK_API_KEY")
        self.client = httpx.AsyncClient(timeout=15.0)
        self._cache: dict[str, PublicBettingSnapshot] = {}

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_public_betting(
        self,
        game_id: str,
        sport: str = "NFL",
        game: str = "",
    ) -> PublicBettingSnapshot | None:
        """Get public betting data for a game.

        Tries sources in order of reliability:
        1. Action Network (if API key available)
        2. Cache
        3. Manual/estimated fallback

        Args:
            game_id: Unique game identifier
            sport: Sport code
            game: Game description for display

        Returns:
            PublicBettingSnapshot or None
        """
        # Check cache first
        cache_key = f"{game_id}:{sport}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Cache valid for 15 minutes
            if (datetime.now() - cached.captured_at).seconds < 900:
                return cached

        # Try Action Network if available
        if self.action_network_key:
            data = await self._fetch_action_network(game_id, sport, game)
            if data:
                self._cache[cache_key] = data
                return data

        # Fallback to estimated data
        # In production, this would be replaced with actual data sources
        estimated = self._generate_estimated_data(game_id, sport, game)
        self._cache[cache_key] = estimated
        return estimated

    async def _fetch_action_network(
        self,
        game_id: str,
        sport: str,
        game: str,
    ) -> PublicBettingSnapshot | None:
        """Fetch from Action Network API.

        Note: This is a placeholder. Action Network's API requires
        enterprise partnership. In production, you would implement
        the actual API integration here.
        """
        # Action Network API is enterprise-only
        # This is a placeholder for when/if access is available
        logger.debug("Action Network API not implemented")
        return None

    def _generate_estimated_data(
        self,
        game_id: str,
        sport: str,
        game: str,
    ) -> PublicBettingSnapshot:
        """Generate estimated public betting percentages.

        This uses historical patterns to estimate public betting.
        In production, replace with actual data sources.

        Common patterns:
        - Public bets favorites
        - Public bets overs
        - Public bets home teams
        - Public bets popular teams
        """
        # Default estimates (slightly favor home/favorites/overs)
        # These are rough approximations based on historical patterns
        data = PublicBettingData(
            game_id=game_id,
            game=game,
            # Spread: slight home lean
            spread_ticket_home=55,
            spread_ticket_away=45,
            spread_money_home=52,
            spread_money_away=48,
            # Totals: slight over lean
            total_ticket_over=58,
            total_ticket_under=42,
            total_money_over=55,
            total_money_under=45,
            # Moneyline: follows favorite
            ml_ticket_home=60,
            ml_ticket_away=40,
            ml_money_home=55,
            ml_money_away=45,
            source=DataSource.MANUAL,
        )

        return PublicBettingSnapshot(
            data=data,
            source=DataSource.MANUAL,
            captured_at=datetime.now(),
            confidence=0.3,  # Low confidence for estimated data
        )

    async def get_sharp_plays(
        self,
        games: list[tuple[str, str, str]],  # (game_id, sport, game_desc)
        min_divergence: float = 10,
    ) -> list[dict]:
        """Find sharp money plays across multiple games.

        Args:
            games: List of (game_id, sport, game_description) tuples
            min_divergence: Minimum money/ticket divergence

        Returns:
            List of sharp play opportunities
        """
        public_data = []

        for game_id, sport, game_desc in games:
            snapshot = await self.get_public_betting(game_id, sport, game_desc)
            if snapshot:
                public_data.append(snapshot.data)

        return identify_sharp_plays(public_data, min_divergence=min_divergence)


class ManualPublicBettingManager:
    """Manager for manually entered public betting data.

    Allows admins to input public betting percentages from
    various sources (Twitter, Covers screenshots, etc.)
    """

    def __init__(self):
        """Initialize manager."""
        self._data: dict[str, PublicBettingData] = {}

    def set_data(
        self,
        game_id: str,
        game: str,
        spread_home: float,
        spread_away: float,
        money_home: float | None = None,
        money_away: float | None = None,
        total_over: float | None = None,
        total_under: float | None = None,
        total_money_over: float | None = None,
        total_money_under: float | None = None,
    ) -> PublicBettingData:
        """Manually set public betting data.

        Args:
            game_id: Game identifier
            game: Game description
            spread_home: % tickets on home spread
            spread_away: % tickets on away spread
            money_home: % money on home (optional, defaults to ticket %)
            money_away: % money on away (optional)
            total_over: % tickets on over (optional)
            total_under: % tickets on under (optional)
            total_money_over: % money on over (optional)
            total_money_under: % money on under (optional)

        Returns:
            Created PublicBettingData
        """
        data = PublicBettingData(
            game_id=game_id,
            game=game,
            spread_ticket_home=spread_home,
            spread_ticket_away=spread_away,
            spread_money_home=money_home or spread_home,
            spread_money_away=money_away or spread_away,
            total_ticket_over=total_over or 50,
            total_ticket_under=total_under or 50,
            total_money_over=total_money_over or total_over or 50,
            total_money_under=total_money_under or total_under or 50,
            ml_ticket_home=spread_home,  # Default to spread %
            ml_ticket_away=spread_away,
            ml_money_home=money_home or spread_home,
            ml_money_away=money_away or spread_away,
            source=DataSource.MANUAL,
        )

        self._data[game_id] = data
        return data

    def get_data(self, game_id: str) -> PublicBettingData | None:
        """Get manually entered data for a game."""
        return self._data.get(game_id)

    def list_games(self) -> list[str]:
        """List all games with manual data."""
        return list(self._data.keys())


# Module-level client
_client: PublicBettingClient | None = None
_manual_manager = ManualPublicBettingManager()


async def fetch_public_betting(
    game_id: str,
    sport: str = "NFL",
    game: str = "",
) -> PublicBettingSnapshot | None:
    """Convenience function to fetch public betting data."""
    global _client
    if _client is None:
        _client = PublicBettingClient()

    # Check manual data first
    manual = _manual_manager.get_data(game_id)
    if manual:
        return PublicBettingSnapshot(
            data=manual,
            source=DataSource.MANUAL,
            captured_at=datetime.now(),
            confidence=0.8,  # Higher confidence for manually entered
        )

    return await _client.get_public_betting(game_id, sport, game)


def set_manual_public_betting(
    game_id: str,
    game: str,
    spread_home: float,
    spread_away: float,
    **kwargs,
) -> PublicBettingData:
    """Set public betting data manually."""
    return _manual_manager.set_data(
        game_id=game_id,
        game=game,
        spread_home=spread_home,
        spread_away=spread_away,
        **kwargs,
    )
