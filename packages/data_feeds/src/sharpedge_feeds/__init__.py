"""SharpEdge Data Feeds - External API clients."""

from sharpedge_feeds.weather_client import (
    WeatherClient,
    get_game_weather,
    GameWeatherData,
)
from sharpedge_feeds.espn_client import (
    ESPNClient,
    get_team_record,
    get_schedule,
    TeamRecord,
    ScheduleGame,
)
from sharpedge_feeds.public_betting_client import (
    PublicBettingClient,
    fetch_public_betting,
)
from sharpedge_feeds.kalshi_client import (
    KalshiClient,
    KalshiConfig,
    KalshiMarket,
    KalshiOrder,
    KalshiPosition,
    get_kalshi_client,
)
from sharpedge_feeds.polymarket_client import (
    PolymarketClient,
    PolymarketConfig,
    PolymarketMarket,
    PolymarketOutcome,
    get_polymarket_client,
)
from sharpedge_feeds.coingecko_client import CoinGeckoClient
from sharpedge_feeds.fec_client import FECClient
from sharpedge_feeds.bls_client import BLSClient

__all__ = [
    # Weather
    "WeatherClient",
    "get_game_weather",
    "GameWeatherData",
    # ESPN
    "ESPNClient",
    "get_team_record",
    "get_schedule",
    "TeamRecord",
    "ScheduleGame",
    # Public Betting
    "PublicBettingClient",
    "fetch_public_betting",
    # Kalshi
    "KalshiClient",
    "KalshiConfig",
    "KalshiMarket",
    "KalshiOrder",
    "KalshiPosition",
    "get_kalshi_client",
    # Polymarket
    "PolymarketClient",
    "PolymarketConfig",
    "PolymarketMarket",
    "PolymarketOutcome",
    "get_polymarket_client",
    # CoinGecko
    "CoinGeckoClient",
    # FEC
    "FECClient",
    # BLS
    "BLSClient",
]
