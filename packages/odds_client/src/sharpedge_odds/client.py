"""HTTP client for The Odds API."""

import logging
from difflib import SequenceMatcher

import httpx

from sharpedge_odds.cache import OddsCache
from sharpedge_odds.constants import (
    BASE_URL,
    BOOKMAKER_DISPLAY_NAMES,
    MARKETS,
    REGIONS,
    SPORT_KEYS,
)
from sharpedge_odds.models import (
    Bookmaker,
    FormattedLine,
    Game,
    LineComparison,
    Market,
    Outcome,
)
from sharpedge_shared.errors import ExternalAPIError
from sharpedge_shared.types import Sport

logger = logging.getLogger("sharpedge.odds")


class OddsClient:
    """Client for The Odds API with caching and rate tracking."""

    def __init__(self, api_key: str, redis_url: str = "") -> None:
        self._api_key = api_key
        self._http = httpx.Client(timeout=30.0)
        self._cache = OddsCache(redis_url) if redis_url else None
        self._remaining_requests: int | None = None
        self._used_requests: int | None = None

    @property
    def remaining_requests(self) -> int | None:
        return self._remaining_requests

    def get_odds(
        self,
        sport: Sport,
        markets: list[str] | None = None,
    ) -> list[Game]:
        """Fetch current odds for a sport from The Odds API."""
        sport_key = SPORT_KEYS.get(sport)
        if not sport_key:
            raise ExternalAPIError("Odds API", f"Unsupported sport: {sport}")

        if markets is None:
            markets = MARKETS

        cache_key = f"{sport_key}:{','.join(markets)}"

        # Check cache
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                logger.debug("Cache hit for %s", cache_key)
                return [Game(**g) for g in cached]

        # Fetch from API
        try:
            response = self._http.get(
                f"{BASE_URL}/sports/{sport_key}/odds",
                params={
                    "apiKey": self._api_key,
                    "regions": ",".join(REGIONS),
                    "markets": ",".join(markets),
                    "oddsFormat": "american",
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise ExternalAPIError("Odds API", str(e)) from e

        # Track API usage from response headers
        self._remaining_requests = _parse_int_header(
            response.headers.get("x-requests-remaining")
        )
        self._used_requests = _parse_int_header(
            response.headers.get("x-requests-used")
        )
        if self._remaining_requests is not None:
            logger.info(
                "Odds API: %d requests remaining, %d used.",
                self._remaining_requests,
                self._used_requests or 0,
            )

        games = [Game(**g) for g in response.json()]

        # Cache the response
        if self._cache:
            self._cache.set(cache_key, [g.model_dump() for g in games])

        return games

    def find_game(
        self,
        query: str,
        sport: Sport | None = None,
    ) -> Game | None:
        """Find a specific game by fuzzy matching team names."""
        query_lower = query.lower().replace("-", " ").replace("vs", " ").strip()

        # Try each sport if none specified
        sports_to_check = [sport] if sport else list(SPORT_KEYS.keys())

        for s in sports_to_check:
            try:
                games = self.get_odds(s)
            except ExternalAPIError:
                continue

            best_match: Game | None = None
            best_score = 0.0

            for game in games:
                game_str = f"{game.home_team} {game.away_team}".lower()
                score = SequenceMatcher(None, query_lower, game_str).ratio()

                # Also check individual team names
                for team in [game.home_team, game.away_team]:
                    team_score = SequenceMatcher(None, query_lower, team.lower()).ratio()
                    score = max(score, team_score)

                if score > best_score:
                    best_score = score
                    best_match = game

            if best_match and best_score > 0.4:
                return best_match

        return None

    def get_line_comparison(self, game: Game) -> LineComparison:
        """Process a game's odds into a comparison-ready format."""
        comparison = LineComparison(
            game_id=game.id,
            home_team=game.home_team,
            away_team=game.away_team,
            commence_time=game.commence_time,
        )

        for book in game.bookmakers:
            display_name = BOOKMAKER_DISPLAY_NAMES.get(book.key, book.title)

            for market in book.markets:
                if market.key == "spreads":
                    for outcome in market.outcomes:
                        line = FormattedLine(
                            sportsbook=book.key,
                            sportsbook_display=display_name,
                            side=outcome.name,
                            line=outcome.point,
                            odds=outcome.price,
                        )
                        if outcome.name == game.home_team:
                            comparison.spread_home.append(line)
                        else:
                            comparison.spread_away.append(line)

                elif market.key == "totals":
                    for outcome in market.outcomes:
                        line = FormattedLine(
                            sportsbook=book.key,
                            sportsbook_display=display_name,
                            side=outcome.name,
                            line=outcome.point,
                            odds=outcome.price,
                        )
                        if outcome.name == "Over":
                            comparison.total_over.append(line)
                        else:
                            comparison.total_under.append(line)

                elif market.key == "h2h":
                    for outcome in market.outcomes:
                        line = FormattedLine(
                            sportsbook=book.key,
                            sportsbook_display=display_name,
                            side=outcome.name,
                            odds=outcome.price,
                        )
                        if outcome.name == game.home_team:
                            comparison.moneyline_home.append(line)
                        else:
                            comparison.moneyline_away.append(line)

        # Mark best lines
        _mark_best_lines(comparison.spread_home, best_fn=_best_spread_home)
        _mark_best_lines(comparison.spread_away, best_fn=_best_spread_away)
        _mark_best_lines(comparison.total_over, best_fn=_best_odds)
        _mark_best_lines(comparison.total_under, best_fn=_best_odds)
        _mark_best_lines(comparison.moneyline_home, best_fn=_best_odds)
        _mark_best_lines(comparison.moneyline_away, best_fn=_best_odds)

        return comparison


def _parse_int_header(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _mark_best_lines(lines: list[FormattedLine], best_fn: callable) -> None:  # type: ignore[type-arg]
    """Mark the best line in a list."""
    if not lines:
        return
    best = best_fn(lines)
    if best:
        best.is_best = True


def _best_odds(lines: list[FormattedLine]) -> FormattedLine | None:
    """Best odds = highest American odds (less negative or more positive)."""
    if not lines:
        return None
    return max(lines, key=lambda l: l.odds)


def _best_spread_home(lines: list[FormattedLine]) -> FormattedLine | None:
    """For home favorite: least negative spread is best, then best odds."""
    if not lines:
        return None
    # Sort by: most favorable spread (closer to 0 for favorite), then best odds
    return max(lines, key=lambda l: (l.line or 0, l.odds))


def _best_spread_away(lines: list[FormattedLine]) -> FormattedLine | None:
    """For away underdog: most positive spread is best, then best odds."""
    if not lines:
        return None
    return max(lines, key=lambda l: (l.line or 0, l.odds))
