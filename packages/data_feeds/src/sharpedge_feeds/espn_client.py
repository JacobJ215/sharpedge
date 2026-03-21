"""ESPN API client for team data and schedules.

ESPN provides free public APIs for sports data.
No authentication required for basic endpoints.
"""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger("sharpedge.feeds.espn")

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

# Sport to ESPN path mapping
SPORT_PATHS = {
    "NFL": "football/nfl",
    "NCAAF": "football/college-football",
    "NBA": "basketball/nba",
    "NCAAB": "basketball/mens-college-basketball",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
}


@dataclass
class TeamRecord:
    """Team record information."""

    team_id: str
    team_name: str
    abbreviation: str
    wins: int
    losses: int
    ties: int
    win_percentage: float
    conference_rank: int | None
    division_rank: int | None
    playoff_seed: int | None
    streak: str  # "W3", "L2", etc.
    home_record: str  # "5-2"
    away_record: str  # "3-4"


@dataclass
class ScheduleGame:
    """A game on a team's schedule."""

    game_id: str
    date: datetime
    home_team: str
    away_team: str
    home_score: int | None
    away_score: int | None
    is_complete: bool
    is_home: bool  # Is the queried team at home
    opponent: str
    result: str | None  # "W", "L", None if not played


class ESPNClient:
    """Client for ESPN API."""

    def __init__(self):
        """Initialize ESPN client."""
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _get_sport_path(self, sport: str) -> str:
        """Get ESPN API path for sport."""
        return SPORT_PATHS.get(sport.upper(), SPORT_PATHS["NFL"])

    async def get_scoreboard(
        self,
        sport: str = "NFL",
        date_str: str | None = None,
    ) -> dict | None:
        """Get scoreboard/schedule for a sport.

        Args:
            sport: Sport code (NFL, NBA, etc.)
            date_str: Date in YYYYMMDD format (optional)

        Returns:
            Raw scoreboard data or None
        """
        try:
            path = self._get_sport_path(sport)
            url = f"{ESPN_API_BASE}/{path}/scoreboard"

            params = {}
            if date_str:
                params["dates"] = date_str

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error("ESPN scoreboard error: %s", e)
            return None

    async def get_team_info(
        self,
        team_id: str,
        sport: str = "NFL",
    ) -> dict | None:
        """Get team information.

        Args:
            team_id: ESPN team ID
            sport: Sport code

        Returns:
            Team data or None
        """
        try:
            path = self._get_sport_path(sport)
            url = f"{ESPN_API_BASE}/{path}/teams/{team_id}"

            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error("ESPN team info error: %s", e)
            return None

    async def get_team_schedule(
        self,
        team_id: str,
        sport: str = "NFL",
        season: int | None = None,
    ) -> list[ScheduleGame]:
        """Get team schedule.

        Args:
            team_id: ESPN team ID
            sport: Sport code
            season: Year (defaults to current)

        Returns:
            List of ScheduleGame
        """
        try:
            path = self._get_sport_path(sport)
            url = f"{ESPN_API_BASE}/{path}/teams/{team_id}/schedule"

            params = {}
            if season:
                params["season"] = season

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            games = []
            team_name = data.get("team", {}).get("displayName", "")

            for event in data.get("events", []):
                game = self._parse_schedule_event(event, team_name)
                if game:
                    games.append(game)

            return games

        except httpx.HTTPError as e:
            logger.error("ESPN schedule error: %s", e)
            return []

    async def get_team_record(
        self,
        team_id: str,
        sport: str = "NFL",
    ) -> TeamRecord | None:
        """Get team record and standings.

        Args:
            team_id: ESPN team ID
            sport: Sport code

        Returns:
            TeamRecord or None
        """
        data = await self.get_team_info(team_id, sport)
        if not data:
            return None

        try:
            team = data.get("team", {})
            record_data = team.get("record", {}).get("items", [{}])[0]
            stats = {s["name"]: s["value"] for s in record_data.get("stats", [])}

            return TeamRecord(
                team_id=team_id,
                team_name=team.get("displayName", ""),
                abbreviation=team.get("abbreviation", ""),
                wins=int(stats.get("wins", 0)),
                losses=int(stats.get("losses", 0)),
                ties=int(stats.get("ties", 0)),
                win_percentage=float(stats.get("winPercent", 0)),
                conference_rank=None,  # Would need standings endpoint
                division_rank=None,
                playoff_seed=None,
                streak=stats.get("streak", ""),
                home_record=record_data.get("summary", "0-0"),
                away_record="",
            )

        except (KeyError, IndexError, ValueError) as e:
            logger.error("Error parsing team record: %s", e)
            return None

    async def search_team(
        self,
        query: str,
        sport: str = "NFL",
    ) -> list[dict]:
        """Search for teams by name.

        Args:
            query: Search query
            sport: Sport code

        Returns:
            List of matching teams
        """
        # ESPN doesn't have a search endpoint, so we get all teams
        # and filter locally
        try:
            path = self._get_sport_path(sport)
            url = f"{ESPN_API_BASE}/{path}/teams"

            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            query_lower = query.lower()
            matches = []

            for group in data.get("sports", [{}])[0].get("leagues", [{}])[0].get(
                "teams", []
            ):
                team = group.get("team", {})
                name = team.get("displayName", "").lower()
                abbrev = team.get("abbreviation", "").lower()

                if query_lower in name or query_lower == abbrev:
                    matches.append(
                        {
                            "id": team.get("id"),
                            "name": team.get("displayName"),
                            "abbreviation": team.get("abbreviation"),
                            "location": team.get("location"),
                        }
                    )

            return matches

        except httpx.HTTPError as e:
            logger.error("ESPN team search error: %s", e)
            return []

    def _parse_schedule_event(
        self,
        event: dict,
        team_name: str,
    ) -> ScheduleGame | None:
        """Parse an event into a ScheduleGame."""
        try:
            competitions = event.get("competitions", [{}])[0]
            competitors = competitions.get("competitors", [])

            if len(competitors) < 2:
                return None

            home_comp = next(
                (c for c in competitors if c.get("homeAway") == "home"), None
            )
            away_comp = next(
                (c for c in competitors if c.get("homeAway") == "away"), None
            )

            if not home_comp or not away_comp:
                return None

            home_team = home_comp.get("team", {}).get("displayName", "")
            away_team = away_comp.get("team", {}).get("displayName", "")

            is_home = home_team == team_name
            opponent = away_team if is_home else home_team

            # Parse scores
            home_score = None
            away_score = None
            is_complete = competitions.get("status", {}).get("type", {}).get(
                "completed", False
            )

            if is_complete:
                home_score = int(home_comp.get("score", 0))
                away_score = int(away_comp.get("score", 0))

            # Determine result
            result = None
            if is_complete:
                if is_home:
                    result = "W" if home_score > away_score else "L"
                else:
                    result = "W" if away_score > home_score else "L"
                if home_score == away_score:
                    result = "T"

            return ScheduleGame(
                game_id=event.get("id", ""),
                date=datetime.fromisoformat(
                    event.get("date", "").replace("Z", "+00:00")
                ),
                home_team=home_team,
                away_team=away_team,
                home_score=home_score,
                away_score=away_score,
                is_complete=is_complete,
                is_home=is_home,
                opponent=opponent,
                result=result,
            )

        except (KeyError, ValueError) as e:
            logger.debug("Error parsing event: %s", e)
            return None


# Module-level client
_client: ESPNClient | None = None


async def get_team_record(
    team_id: str,
    sport: str = "NFL",
) -> TeamRecord | None:
    """Convenience function to get team record."""
    global _client
    if _client is None:
        _client = ESPNClient()
    return await _client.get_team_record(team_id, sport)


async def get_schedule(
    team_id: str,
    sport: str = "NFL",
) -> list[ScheduleGame]:
    """Convenience function to get team schedule."""
    global _client
    if _client is None:
        _client = ESPNClient()
    return await _client.get_team_schedule(team_id, sport)
