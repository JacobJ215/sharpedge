"""Feature assembler helper data and functions.

Extracted from feature_assembler.py to keep that module under 500 lines.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Team timezone lookup
# ---------------------------------------------------------------------------

TEAM_TIMEZONES: dict[str, str] = {
    # --- NFL teams ---
    "Arizona Cardinals": "America/Phoenix",
    "Atlanta Falcons": "America/New_York",
    "Baltimore Ravens": "America/New_York",
    "Buffalo Bills": "America/New_York",
    "Carolina Panthers": "America/New_York",
    "Chicago Bears": "America/Chicago",
    "Cincinnati Bengals": "America/New_York",
    "Cleveland Browns": "America/New_York",
    "Dallas Cowboys": "America/Chicago",
    "Denver Broncos": "America/Denver",
    "Detroit Lions": "America/Detroit",
    "Green Bay Packers": "America/Chicago",
    "Houston Texans": "America/Chicago",
    "Indianapolis Colts": "America/Indiana/Indianapolis",
    "Jacksonville Jaguars": "America/New_York",
    "Kansas City Chiefs": "America/Chicago",
    "Las Vegas Raiders": "America/Los_Angeles",
    "Los Angeles Chargers": "America/Los_Angeles",
    "Los Angeles Rams": "America/Los_Angeles",
    "Miami Dolphins": "America/New_York",
    "Minnesota Vikings": "America/Chicago",
    "New England Patriots": "America/New_York",
    "New Orleans Saints": "America/Chicago",
    "New York Giants": "America/New_York",
    "New York Jets": "America/New_York",
    "Philadelphia Eagles": "America/New_York",
    "Pittsburgh Steelers": "America/New_York",
    "San Francisco 49ers": "America/Los_Angeles",
    "Seattle Seahawks": "America/Los_Angeles",
    "Tampa Bay Buccaneers": "America/New_York",
    "Tennessee Titans": "America/Chicago",
    "Washington Commanders": "America/New_York",
    # --- NBA teams ---
    "Atlanta Hawks": "America/New_York",
    "Boston Celtics": "America/New_York",
    "Brooklyn Nets": "America/New_York",
    "Charlotte Hornets": "America/New_York",
    "Chicago Bulls": "America/Chicago",
    "Cleveland Cavaliers": "America/New_York",
    "Dallas Mavericks": "America/Chicago",
    "Denver Nuggets": "America/Denver",
    "Detroit Pistons": "America/Detroit",
    "Golden State Warriors": "America/Los_Angeles",
    "Houston Rockets": "America/Chicago",
    "Indiana Pacers": "America/Indiana/Indianapolis",
    "Los Angeles Clippers": "America/Los_Angeles",
    "Los Angeles Lakers": "America/Los_Angeles",
    "Memphis Grizzlies": "America/Chicago",
    "Miami Heat": "America/New_York",
    "Milwaukee Bucks": "America/Chicago",
    "Minnesota Timberwolves": "America/Chicago",
    "New Orleans Pelicans": "America/Chicago",
    "New York Knicks": "America/New_York",
    "Oklahoma City Thunder": "America/Chicago",
    "Orlando Magic": "America/New_York",
    "Philadelphia 76ers": "America/New_York",
    "Phoenix Suns": "America/Phoenix",
    "Portland Trail Blazers": "America/Los_Angeles",
    "Sacramento Kings": "America/Los_Angeles",
    "San Antonio Spurs": "America/Chicago",
    "Toronto Raptors": "America/Toronto",
    "Utah Jazz": "America/Denver",
    "Washington Wizards": "America/New_York",
}

# Injury status -> strength impact mapping
STATUS_IMPACT: dict[str, float] = {
    "Out": -1.0,
    "Doubtful": -0.6,
    "Questionable": -0.3,
    "Day-To-Day": -0.2,
}

# Reference datetime for UTC offset computation (avoid DST edge cases)
_OFFSET_REFERENCE = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def compute_timezone_crossings(away_team: str, home_team: str) -> int:
    """Compute absolute timezone hour difference between away and home team home cities.

    Args:
        away_team: Name of the away team.
        home_team: Name of the home team (venue owner; used only as baseline).

    Returns:
        Absolute integer hour difference between teams' home city timezones.
        Returns 0 if either team is not found in TEAM_TIMEZONES.
    """
    from zoneinfo import ZoneInfo

    away_tz_name = TEAM_TIMEZONES.get(away_team)
    home_tz_name = TEAM_TIMEZONES.get(home_team)

    if not away_tz_name or not home_tz_name:
        return 0

    try:
        away_tz = ZoneInfo(away_tz_name)
        home_tz = ZoneInfo(home_tz_name)

        away_offset = _OFFSET_REFERENCE.astimezone(away_tz).utcoffset()
        home_offset = _OFFSET_REFERENCE.astimezone(home_tz).utcoffset()

        if away_offset is None or home_offset is None:
            return 0

        diff_hours = abs(
            int(away_offset.total_seconds() / 3600)
            - int(home_offset.total_seconds() / 3600)
        )
        return diff_hours

    except Exception:
        logger.debug(
            "Failed to compute timezone crossings for %s vs %s",
            away_team,
            home_team,
        )
        return 0


def travel_penalty_from_crossings(crossings: int) -> float:
    """Map timezone crossing count to travel penalty value.

    Args:
        crossings: Number of timezone hours between team home cities.

    Returns:
        0.0 for 0-1 crossings, -0.15 for 2, -0.3 for 3+.
    """
    if crossings >= 3:
        return -0.3
    if crossings == 2:
        return -0.15
    return 0.0


def compute_form_stats(
    home_team: str,
    home_rows: list[dict],
    away_team: str,
    away_rows: list[dict],
) -> dict:
    """Compute rolling form statistics from historical game rows."""
    result: dict = {}

    for label, team, rows in [("home", home_team, home_rows), ("away", away_team, away_rows)]:
        scores_for: list[float] = []
        scores_against: list[float] = []
        ats_results: list[int] = []

        for row in rows:
            is_home = row.get("home_team") == team
            if is_home:
                s_for = row.get("home_score")
                s_against = row.get("away_score")
            else:
                s_for = row.get("away_score")
                s_against = row.get("home_score")

            if s_for is not None:
                scores_for.append(float(s_for))
            if s_against is not None:
                scores_against.append(float(s_against))

            sr = row.get("spread_result")
            if sr == "cover":
                ats_results.append(1)
            elif sr == "loss":
                ats_results.append(0)

        if scores_for:
            result[f"{label}_ppg_10g"] = sum(scores_for) / len(scores_for)
            result[f"{label}_ppg_5g"] = result[f"{label}_ppg_10g"]
        if scores_against:
            result[f"{label}_papg_10g"] = sum(scores_against) / len(scores_against)
            result[f"{label}_papg_5g"] = result[f"{label}_papg_10g"]
        if ats_results:
            result[f"{label}_ats_10g"] = sum(ats_results) / len(ats_results)

    return result


def parse_injury_impact(
    scoreboard: dict | None, home_team: str, away_team: str
) -> tuple[float, float]:
    """Parse ESPN scoreboard response for injury impact scores.

    Returns (home_impact, away_impact) as floats (0.0 when no injuries found).
    """
    if not scoreboard:
        return (0.0, 0.0)

    home_impact = 0.0
    away_impact = 0.0

    try:
        events = scoreboard.get("events", [])
        for event in events:
            for competition in event.get("competitions", []):
                for competitor in competition.get("competitors", []):
                    team_name = (
                        competitor.get("team", {}).get("displayName", "")
                        or competitor.get("team", {}).get("name", "")
                    )
                    injuries = competitor.get("injuries", [])
                    impact = sum(
                        STATUS_IMPACT.get(inj.get("status", ""), 0.0)
                        for inj in injuries
                    )
                    if team_name == home_team:
                        home_impact = impact
                    elif team_name == away_team:
                        away_impact = impact
    except Exception:
        logger.debug("Error parsing injury data")

    return (home_impact, away_impact)


def sync_get_public_betting(client, game_id: str, sport: str):
    """Best-effort synchronous wrapper for async PublicBettingClient.

    Returns None when the event loop is unavailable (e.g. sync context).
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        return loop.run_until_complete(client.get_public_betting(game_id, sport))
    except Exception:
        return None


def sync_get_weather_score(client, home_team: str, sport: str) -> float | None:
    """Best-effort synchronous call to async WeatherClient.

    Returns None when unavailable.
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None
        game_time = datetime.now(timezone.utc)
        weather_data = loop.run_until_complete(
            client.get_game_weather("unknown", home_team, game_time, sport.upper())
        )
        if weather_data is None:
            return None
        impact = weather_data.impact
        return float(getattr(impact, "impact_score", 0.0))
    except Exception:
        return None


def query_rest_days(db, team: str, game_date: str) -> int | None:
    """Query DB for last game date before game_date; return day diff."""
    try:
        rows = (
            db.table("historical_games")
            .select("game_date")
            .or_(f"home_team.eq.{team},away_team.eq.{team}")
            .lt("game_date", game_date)
            .order("game_date", desc=True)
            .limit(1)
            .execute()
        )
        data = rows.data or []
        if not data:
            return None
        last_date = datetime.fromisoformat(data[0]["game_date"]).date()
        target_date = datetime.fromisoformat(game_date).date()
        return (target_date - last_date).days
    except Exception:
        return None
