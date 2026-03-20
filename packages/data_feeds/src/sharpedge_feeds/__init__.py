"""SharpEdge Data Feeds - External API clients."""

try:
    from sharpedge_feeds.weather_client import (
        WeatherClient,
        get_game_weather,
        GameWeatherData,
    )
except ImportError:
    WeatherClient = None  # type: ignore[assignment,misc]
    get_game_weather = None  # type: ignore[assignment]
    GameWeatherData = None  # type: ignore[assignment,misc]

try:
    from sharpedge_feeds.espn_client import (
        ESPNClient,
        get_team_record,
        get_schedule,
        TeamRecord,
        ScheduleGame,
    )
except ImportError:
    ESPNClient = None  # type: ignore[assignment,misc]
    get_team_record = None  # type: ignore[assignment]
    get_schedule = None  # type: ignore[assignment]
    TeamRecord = None  # type: ignore[assignment,misc]
    ScheduleGame = None  # type: ignore[assignment,misc]

try:
    from sharpedge_feeds.public_betting_client import (
        PublicBettingClient,
        fetch_public_betting,
    )
except ImportError:
    PublicBettingClient = None  # type: ignore[assignment,misc]
    fetch_public_betting = None  # type: ignore[assignment]
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
from sharpedge_feeds.kalshi_stream import KalshiStreamClient, KalshiTick
from sharpedge_feeds.polymarket_stream import PolymarketStreamClient, PolyTick
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
    # Streaming
    "KalshiStreamClient",
    "KalshiTick",
    "PolymarketStreamClient",
    "PolyTick",
    # CoinGecko
    "CoinGeckoClient",
    # FEC
    "FECClient",
    # BLS
    "BLSClient",
]
