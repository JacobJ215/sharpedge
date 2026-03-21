"""Business logic for odds and line comparisons."""

import logging

from sharpedge_odds.client import OddsClient
from sharpedge_odds.models import LineComparison
from sharpedge_shared.errors import ExternalAPIError
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.services.odds")

_client: OddsClient | None = None


def get_odds_client(api_key: str, redis_url: str = "") -> OddsClient:
    """Get or create the singleton OddsClient."""
    global _client
    if _client is None:
        _client = OddsClient(api_key=api_key, redis_url=redis_url)
    return _client


def get_lines_for_game(
    game_query: str,
    api_key: str,
    redis_url: str = "",
    sport: Sport | None = None,
) -> LineComparison:
    """Find a game and return formatted line comparison."""
    client = get_odds_client(api_key, redis_url)
    game = client.find_game(game_query, sport)
    if game is None:
        raise ExternalAPIError("Odds API", f"Could not find game matching '{game_query}'")
    return client.get_line_comparison(game)
