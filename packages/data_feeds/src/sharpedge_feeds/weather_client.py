"""Weather API client for game weather data.

Uses WeatherAPI.com for weather forecasts.
Free tier: 1M calls/month, 3-day forecast.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime

import httpx
from sharpedge_analytics import (
    VenueType,
    WeatherConditions,
    WeatherImpact,
    calculate_weather_impact,
)

logger = logging.getLogger("sharpedge.feeds.weather")

WEATHER_API_BASE = "https://api.weatherapi.com/v1"


@dataclass
class GameWeatherData:
    """Weather data for a specific game."""

    game_id: str
    venue: str
    venue_type: VenueType
    conditions: WeatherConditions
    impact: WeatherImpact
    forecast_time: datetime


# NFL Stadium locations for weather lookups
NFL_STADIUMS = {
    "Arizona Cardinals": ("Glendale, AZ", "State Farm Stadium", VenueType.DOME),
    "Atlanta Falcons": ("Atlanta, GA", "Mercedes-Benz Stadium", VenueType.DOME),
    "Baltimore Ravens": ("Baltimore, MD", "M&T Bank Stadium", VenueType.OUTDOOR),
    "Buffalo Bills": ("Orchard Park, NY", "Highmark Stadium", VenueType.OUTDOOR),
    "Carolina Panthers": ("Charlotte, NC", "Bank of America Stadium", VenueType.OUTDOOR),
    "Chicago Bears": ("Chicago, IL", "Soldier Field", VenueType.OUTDOOR),
    "Cincinnati Bengals": ("Cincinnati, OH", "Paycor Stadium", VenueType.OUTDOOR),
    "Cleveland Browns": ("Cleveland, OH", "Cleveland Browns Stadium", VenueType.OUTDOOR),
    "Dallas Cowboys": ("Arlington, TX", "AT&T Stadium", VenueType.DOME),
    "Denver Broncos": ("Denver, CO", "Empower Field", VenueType.OUTDOOR),
    "Detroit Lions": ("Detroit, MI", "Ford Field", VenueType.DOME),
    "Green Bay Packers": ("Green Bay, WI", "Lambeau Field", VenueType.OUTDOOR),
    "Houston Texans": ("Houston, TX", "NRG Stadium", VenueType.RETRACTABLE),
    "Indianapolis Colts": ("Indianapolis, IN", "Lucas Oil Stadium", VenueType.DOME),
    "Jacksonville Jaguars": ("Jacksonville, FL", "TIAA Bank Field", VenueType.OUTDOOR),
    "Kansas City Chiefs": ("Kansas City, MO", "Arrowhead Stadium", VenueType.OUTDOOR),
    "Las Vegas Raiders": ("Las Vegas, NV", "Allegiant Stadium", VenueType.DOME),
    "Los Angeles Chargers": ("Inglewood, CA", "SoFi Stadium", VenueType.DOME),
    "Los Angeles Rams": ("Inglewood, CA", "SoFi Stadium", VenueType.DOME),
    "Miami Dolphins": ("Miami Gardens, FL", "Hard Rock Stadium", VenueType.OUTDOOR),
    "Minnesota Vikings": ("Minneapolis, MN", "U.S. Bank Stadium", VenueType.DOME),
    "New England Patriots": ("Foxborough, MA", "Gillette Stadium", VenueType.OUTDOOR),
    "New Orleans Saints": ("New Orleans, LA", "Caesars Superdome", VenueType.DOME),
    "New York Giants": ("East Rutherford, NJ", "MetLife Stadium", VenueType.OUTDOOR),
    "New York Jets": ("East Rutherford, NJ", "MetLife Stadium", VenueType.OUTDOOR),
    "Philadelphia Eagles": ("Philadelphia, PA", "Lincoln Financial Field", VenueType.OUTDOOR),
    "Pittsburgh Steelers": ("Pittsburgh, PA", "Acrisure Stadium", VenueType.OUTDOOR),
    "San Francisco 49ers": ("Santa Clara, CA", "Levi's Stadium", VenueType.OUTDOOR),
    "Seattle Seahawks": ("Seattle, WA", "Lumen Field", VenueType.OUTDOOR),
    "Tampa Bay Buccaneers": ("Tampa, FL", "Raymond James Stadium", VenueType.OUTDOOR),
    "Tennessee Titans": ("Nashville, TN", "Nissan Stadium", VenueType.OUTDOOR),
    "Washington Commanders": ("Landover, MD", "FedExField", VenueType.OUTDOOR),
}


class WeatherClient:
    """Client for fetching weather data."""

    def __init__(self, api_key: str | None = None):
        """Initialize weather client.

        Args:
            api_key: WeatherAPI.com API key. Falls back to WEATHER_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("WEATHER_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_forecast(
        self,
        location: str,
        date: datetime | None = None,
    ) -> dict | None:
        """Get weather forecast for a location.

        Args:
            location: City, state or coordinates
            date: Date for forecast (default: today)

        Returns:
            Raw forecast data or None if failed
        """
        if not self.api_key:
            logger.warning("No weather API key configured")
            return None

        try:
            params = {
                "key": self.api_key,
                "q": location,
                "days": 3,
                "aqi": "no",
                "alerts": "no",
            }

            response = await self.client.get(
                f"{WEATHER_API_BASE}/forecast.json",
                params=params,
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error("Weather API error for %s: %s", location, e)
            return None

    async def get_game_weather(
        self,
        game_id: str,
        home_team: str,
        game_time: datetime,
        sport: str = "NFL",
    ) -> GameWeatherData | None:
        """Get weather for a specific game.

        Args:
            game_id: Unique game identifier
            home_team: Home team name for venue lookup
            game_time: Game start time
            sport: Sport for impact calculation

        Returns:
            GameWeatherData or None if unavailable
        """
        # Look up stadium info
        stadium_info = NFL_STADIUMS.get(home_team)
        if not stadium_info:
            # Try partial match
            for team, info in NFL_STADIUMS.items():
                if home_team in team or team in home_team:
                    stadium_info = info
                    break

        if not stadium_info:
            logger.warning("Unknown team: %s", home_team)
            return None

        location, venue, venue_type = stadium_info

        # Dome games don't need weather
        if venue_type == VenueType.DOME:
            conditions = WeatherConditions(
                temperature=72,
                wind_speed=0,
                wind_direction="",
                precipitation_chance=0,
                precipitation_type=None,
                humidity=50,
                conditions="Indoor",
            )
            impact = calculate_weather_impact(conditions, sport, venue_type)
            return GameWeatherData(
                game_id=game_id,
                venue=venue,
                venue_type=venue_type,
                conditions=conditions,
                impact=impact,
                forecast_time=game_time,
            )

        # Fetch forecast
        forecast = await self.get_forecast(location, game_time)
        if not forecast:
            return None

        # Find the hour closest to game time
        try:
            forecast_day = None
            game_date_str = game_time.strftime("%Y-%m-%d")

            for day in forecast.get("forecast", {}).get("forecastday", []):
                if day.get("date") == game_date_str:
                    forecast_day = day
                    break

            if not forecast_day:
                # Use first day if date not found
                forecast_day = forecast["forecast"]["forecastday"][0]

            # Find closest hour
            game_hour = game_time.hour
            closest_hour = None
            min_diff = 24

            for hour in forecast_day.get("hour", []):
                hour_time = datetime.fromisoformat(hour["time"])
                diff = abs(hour_time.hour - game_hour)
                if diff < min_diff:
                    min_diff = diff
                    closest_hour = hour

            if not closest_hour:
                closest_hour = forecast_day["hour"][12]  # Noon fallback

            # Parse conditions
            conditions = WeatherConditions(
                temperature=closest_hour.get("temp_f", 70),
                wind_speed=closest_hour.get("wind_mph", 0),
                wind_direction=closest_hour.get("wind_dir", ""),
                precipitation_chance=closest_hour.get("chance_of_rain", 0)
                + closest_hour.get("chance_of_snow", 0),
                precipitation_type=_get_precip_type(closest_hour),
                humidity=closest_hour.get("humidity", 50),
                conditions=closest_hour.get("condition", {}).get("text", "Unknown"),
            )

            impact = calculate_weather_impact(conditions, sport, venue_type)

            return GameWeatherData(
                game_id=game_id,
                venue=venue,
                venue_type=venue_type,
                conditions=conditions,
                impact=impact,
                forecast_time=game_time,
            )

        except (KeyError, IndexError) as e:
            logger.error("Error parsing weather data: %s", e)
            return None


def _get_precip_type(hour_data: dict) -> str | None:
    """Determine precipitation type from forecast data."""
    if hour_data.get("chance_of_snow", 0) > 30:
        return "snow"
    if hour_data.get("chance_of_rain", 0) > 30:
        return "rain"
    return None


# Module-level client instance
_client: WeatherClient | None = None


async def get_game_weather(
    game_id: str,
    home_team: str,
    game_time: datetime,
    sport: str = "NFL",
) -> GameWeatherData | None:
    """Convenience function to get game weather.

    Args:
        game_id: Unique game identifier
        home_team: Home team name
        game_time: Game start time
        sport: Sport for impact calculation

    Returns:
        GameWeatherData or None
    """
    global _client
    if _client is None:
        _client = WeatherClient()

    return await _client.get_game_weather(game_id, home_team, game_time, sport)
