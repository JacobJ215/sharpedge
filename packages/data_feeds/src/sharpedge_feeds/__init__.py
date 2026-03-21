"""SharpEdge Data Feeds - External API clients."""

try:
    from sharpedge_feeds.weather_client import (
        GameWeatherData,
        WeatherClient,
        get_game_weather,
    )
except ImportError:
    WeatherClient = None  # type: ignore[assignment,misc]
    get_game_weather = None  # type: ignore[assignment]
    GameWeatherData = None  # type: ignore[assignment,misc]

try:
    from sharpedge_feeds.espn_client import (
        ESPNClient,
        ScheduleGame,
        TeamRecord,
        get_schedule,
        get_team_record,
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
from sharpedge_feeds.bls_client import BLSClient
from sharpedge_feeds.coingecko_client import CoinGeckoClient
from sharpedge_feeds.fec_client import FECClient
from sharpedge_feeds.kalshi_client import (
    KalshiClient,
    KalshiConfig,
    KalshiMarket,
    KalshiOrder,
    KalshiPosition,
    get_kalshi_client,
)
from sharpedge_feeds.kalshi_stream import KalshiStreamClient, KalshiTick
from sharpedge_feeds.polymarket_client import (
    PolymarketClient,
    PolymarketConfig,
    PolymarketMarket,
    PolymarketOutcome,
    get_polymarket_client,
)
from sharpedge_feeds.polymarket_stream import PolymarketStreamClient, PolyTick

__all__ = [
    # BLS
    "BLSClient",
    # CoinGecko
    "CoinGeckoClient",
    # ESPN
    "ESPNClient",
    # FEC
    "FECClient",
    "GameWeatherData",
    # Kalshi
    "KalshiClient",
    "KalshiConfig",
    "KalshiMarket",
    "KalshiOrder",
    "KalshiPosition",
    # Streaming
    "KalshiStreamClient",
    "KalshiTick",
    "PolyTick",
    # Polymarket
    "PolymarketClient",
    "PolymarketConfig",
    "PolymarketMarket",
    "PolymarketOutcome",
    "PolymarketStreamClient",
    # Public Betting
    "PublicBettingClient",
    "ScheduleGame",
    "TeamRecord",
    # Weather
    "WeatherClient",
    "fetch_public_betting",
    "get_game_weather",
    "get_kalshi_client",
    "get_polymarket_client",
    "get_schedule",
    "get_team_record",
]
