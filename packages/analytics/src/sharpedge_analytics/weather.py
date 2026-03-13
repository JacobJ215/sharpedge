"""Weather impact analysis for sports betting.

Weather significantly affects outdoor sports, especially totals.
High winds, extreme temperatures, and precipitation all impact scoring.
"""

from dataclasses import dataclass
from enum import StrEnum


class VenueType(StrEnum):
    """Type of venue for weather consideration."""

    OUTDOOR = "outdoor"
    DOME = "dome"
    RETRACTABLE = "retractable"  # May be open or closed


@dataclass
class WeatherConditions:
    """Weather data for a game."""

    temperature: float  # Fahrenheit
    wind_speed: float  # MPH
    wind_direction: str  # "N", "NE", "E", etc.
    precipitation_chance: float  # 0-100 percentage
    precipitation_type: str | None  # "rain", "snow", "sleet", None
    humidity: float  # 0-100 percentage
    conditions: str  # "Clear", "Cloudy", "Rain", etc.


@dataclass
class WeatherImpact:
    """Calculated impact of weather on a game."""

    total_adjustment: float  # Points to adjust total
    spread_adjustment: float  # Points to adjust spread
    impact_level: str  # "none", "minor", "moderate", "severe"
    factors: list[str]  # List of significant factors
    betting_implications: list[str]  # Actionable insights
    raw_conditions: WeatherConditions


# Dome stadiums (no weather impact)
DOME_STADIUMS = {
    "NFL": [
        "AT&T Stadium",  # Cowboys
        "Caesars Superdome",  # Saints
        "Ford Field",  # Lions
        "Lucas Oil Stadium",  # Colts
        "Allegiant Stadium",  # Raiders
        "State Farm Stadium",  # Cardinals
        "U.S. Bank Stadium",  # Vikings
        "Mercedes-Benz Stadium",  # Falcons
        "NRG Stadium",  # Texans (retractable)
        "SoFi Stadium",  # Rams/Chargers
    ],
    "MLB": [
        "Tropicana Field",  # Rays
        "Globe Life Field",  # Rangers
        "Chase Field",  # Diamondbacks (retractable)
        "Minute Maid Park",  # Astros (retractable)
        "Rogers Centre",  # Blue Jays (retractable)
        "Miller Park",  # Brewers (retractable)
        "T-Mobile Park",  # Mariners (retractable)
        "loanDepot Park",  # Marlins (retractable)
    ],
}


def get_venue_type(stadium: str, sport: str = "NFL") -> VenueType:
    """Determine if a stadium is a dome, outdoor, or retractable."""
    domes = DOME_STADIUMS.get(sport.upper(), [])

    for dome in domes:
        if dome.lower() in stadium.lower() or stadium.lower() in dome.lower():
            if "retractable" in dome.lower() or stadium.lower() in [
                "nrg", "chase", "minute maid", "rogers", "miller",
                "t-mobile", "loandepot"
            ]:
                return VenueType.RETRACTABLE
            return VenueType.DOME

    return VenueType.OUTDOOR


def calculate_weather_impact(
    conditions: WeatherConditions,
    sport: str = "NFL",
    venue_type: VenueType = VenueType.OUTDOOR,
) -> WeatherImpact:
    """Calculate the betting impact of weather conditions.

    Args:
        conditions: Weather data
        sport: Sport for impact calculation
        venue_type: Type of venue

    Returns:
        WeatherImpact with adjustments and insights
    """
    # No impact for dome games
    if venue_type == VenueType.DOME:
        return WeatherImpact(
            total_adjustment=0,
            spread_adjustment=0,
            impact_level="none",
            factors=["Indoor venue - no weather impact"],
            betting_implications=[],
            raw_conditions=conditions,
        )

    total_adj = 0
    spread_adj = 0
    factors = []
    implications = []

    # Wind impact (most significant for NFL/NCAAF)
    if sport.upper() in ["NFL", "NCAAF"]:
        if conditions.wind_speed >= 20:
            wind_adj = -((conditions.wind_speed - 15) * 0.2)
            total_adj += wind_adj
            factors.append(f"High wind ({conditions.wind_speed:.0f} mph): {wind_adj:.1f} pts")
            implications.append("Expect more running, shorter passes")
            implications.append("Field goal accuracy significantly impacted")
        elif conditions.wind_speed >= 15:
            wind_adj = -1.0
            total_adj += wind_adj
            factors.append(f"Moderate wind ({conditions.wind_speed:.0f} mph): {wind_adj:.1f} pts")
            implications.append("Deep passing game may be affected")

    # Temperature impact
    if conditions.temperature < 32:
        temp_adj = -1.5
        total_adj += temp_adj
        factors.append(f"Extreme cold ({conditions.temperature:.0f}°F): {temp_adj:.1f} pts")
        implications.append("Ball handling issues, shorter game")
        implications.append("Expect conservative play calling")
    elif conditions.temperature < 40:
        temp_adj = -0.5
        total_adj += temp_adj
        factors.append(f"Cold weather ({conditions.temperature:.0f}°F): {temp_adj:.1f} pts")
    elif conditions.temperature > 90:
        temp_adj = -0.5
        total_adj += temp_adj
        factors.append(f"Extreme heat ({conditions.temperature:.0f}°F): {temp_adj:.1f} pts")
        implications.append("Player fatigue may be a factor late")

    # Precipitation impact
    if conditions.precipitation_chance >= 70:
        if conditions.precipitation_type == "snow":
            precip_adj = -3.0
            total_adj += precip_adj
            factors.append(f"Snow expected ({conditions.precipitation_chance:.0f}%): {precip_adj:.1f} pts")
            implications.append("Heavy snow games historically very low scoring")
            implications.append("Running game will dominate")
        elif conditions.precipitation_type == "rain":
            precip_adj = -1.5
            total_adj += precip_adj
            factors.append(f"Rain expected ({conditions.precipitation_chance:.0f}%): {precip_adj:.1f} pts")
            implications.append("Wet ball affects passing and catching")
    elif conditions.precipitation_chance >= 40:
        precip_adj = -0.5
        total_adj += precip_adj
        factors.append(f"Chance of precipitation ({conditions.precipitation_chance:.0f}%)")

    # Determine impact level
    if abs(total_adj) >= 3:
        impact_level = "severe"
    elif abs(total_adj) >= 1.5:
        impact_level = "moderate"
    elif abs(total_adj) >= 0.5:
        impact_level = "minor"
    else:
        impact_level = "none"
        if not factors:
            factors.append("Weather conditions favorable for normal play")

    return WeatherImpact(
        total_adjustment=round(total_adj, 1),
        spread_adjustment=round(spread_adj, 1),
        impact_level=impact_level,
        factors=factors,
        betting_implications=implications,
        raw_conditions=conditions,
    )


def get_weather_betting_advice(impact: WeatherImpact) -> list[str]:
    """Generate specific betting advice based on weather impact.

    Args:
        impact: WeatherImpact from calculate_weather_impact

    Returns:
        List of actionable betting recommendations
    """
    advice = []

    if impact.impact_level == "none":
        return ["No weather-based adjustments needed"]

    if impact.total_adjustment <= -2:
        advice.append(f"Strong lean to UNDER (adjust total by {impact.total_adjustment:.1f} pts)")
    elif impact.total_adjustment <= -1:
        advice.append(f"Slight lean to UNDER (adjust total by {impact.total_adjustment:.1f} pts)")

    if impact.raw_conditions.wind_speed >= 20:
        advice.append("Avoid player props for deep ball receivers")
        advice.append("Consider rushing props over passing")
        advice.append("Field goal kicker props risky")

    if impact.raw_conditions.temperature < 32:
        advice.append("Cold weather favorites historically cover at higher rate")

    if impact.raw_conditions.precipitation_type == "snow":
        advice.append("Snow games are historically profitable UNDER plays")

    return advice if advice else ["Monitor conditions closer to game time"]


def format_weather_display(conditions: WeatherConditions) -> str:
    """Format weather conditions for display."""
    parts = [
        f"{conditions.temperature:.0f}°F",
        conditions.conditions,
    ]

    if conditions.wind_speed >= 10:
        parts.append(f"Wind {conditions.wind_speed:.0f} mph {conditions.wind_direction}")

    if conditions.precipitation_chance >= 30:
        precip = conditions.precipitation_type or "precipitation"
        parts.append(f"{conditions.precipitation_chance:.0f}% chance {precip}")

    return " | ".join(parts)
