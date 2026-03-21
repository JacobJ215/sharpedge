"""FeatureAssembler — assembles MODEL-02 game feature vector at inference time.

All external data sources fail gracefully to sport-specific medians.
Do NOT cache results — features are assembled fresh per inference call.

Helper data (TEAM_TIMEZONES, STATUS_IMPACT) and pure functions
(compute_timezone_crossings, travel_penalty_from_crossings, etc.)
live in _feature_helpers.py to keep this file under 500 lines.
"""

import logging
from datetime import datetime

from sharpedge_models._feature_helpers import (  # noqa: F401 — re-exported for callers
    TEAM_TIMEZONES,
    compute_form_stats,
    compute_timezone_crossings,
    parse_injury_impact,
    query_rest_days,
    sync_get_public_betting,
    sync_get_weather_score,
    travel_penalty_from_crossings,
)
from sharpedge_models.ml_inference import GameFeatures

logger = logging.getLogger(__name__)


class FeatureAssembler:
    """Assembles MODEL-02 game feature vector at inference time.

    All external data sources fail gracefully to sport-specific medians.
    Do NOT cache results — features are assembled fresh per inference call.
    """

    def __init__(
        self,
        supabase_client=None,
        espn_client=None,
        public_betting_client=None,
        weather_client=None,
    ) -> None:
        self._db = supabase_client
        self._espn = espn_client
        self._betting = public_betting_client
        self._weather = weather_client

    def assemble(self, game_context: dict) -> GameFeatures:
        """Assemble a complete GameFeatures from game_context dict.

        Args:
            game_context: Dict containing at minimum home_team, away_team, sport.
                          May also contain line_movements, game_date, spread_line,
                          total_line, and other optional fields.

        Returns:
            GameFeatures instance. None values in non-required fields will be
            imputed with sport-specific medians in to_array().
        """
        home_team: str = game_context.get("home_team", "")
        away_team: str = game_context.get("away_team", "")
        sport: str = game_context.get("sport", "")
        game_date: str = game_context.get("game_date", "")

        form = self._team_form(home_team, away_team, sport)
        h2h = self._matchup_history(home_team, away_team, sport)
        home_inj, away_inj = self._injury_impact(home_team, away_team, sport)
        sentiment = self._market_sentiment(game_context)
        weather_score, t_penalty = self._weather_travel(home_team, away_team, sport)
        home_rest, away_rest = self._rest_days(home_team, away_team, sport, game_date)

        return GameFeatures(
            home_team=home_team,
            away_team=away_team,
            sport=sport,
            spread_line=game_context.get("spread_line"),
            total_line=game_context.get("total_line"),
            # 5g form
            home_ppg_5g=form.get("home_ppg_5g"),
            home_papg_5g=form.get("home_papg_5g"),
            away_ppg_5g=form.get("away_ppg_5g"),
            away_papg_5g=form.get("away_papg_5g"),
            # ATS
            home_ats_10g=form.get("home_ats_10g"),
            away_ats_10g=form.get("away_ats_10g"),
            # Rest days
            home_rest_days=home_rest,
            away_rest_days=away_rest,
            # MODEL-02: 10g rolling form
            home_ppg_10g=form.get("home_ppg_10g"),
            home_papg_10g=form.get("home_papg_10g"),
            away_ppg_10g=form.get("away_ppg_10g"),
            away_papg_10g=form.get("away_papg_10g"),
            # MODEL-02: H2H matchup history
            h2h_home_cover_rate=h2h.get("h2h_home_cover_rate"),
            h2h_total_games=h2h.get("h2h_total_games"),
            # MODEL-02: Injury impact
            home_injury_impact=home_inj,
            away_injury_impact=away_inj,
            # MODEL-02: Market sentiment
            line_movement_velocity=sentiment.get("line_movement_velocity"),
            public_pct_home=sentiment.get("public_pct_home"),
            # MODEL-02: Weather / travel
            weather_impact_score=weather_score,
            travel_penalty=t_penalty,
            # MODEL-02: Cross-cutting (None → median imputation in to_array)
            home_away_split_delta=None,
            opponent_strength_home=None,
            opponent_strength_away=None,
            key_number_proximity=None,
        )

    # ------------------------------------------------------------------
    # Private helpers — each returns partial dict or scalar(s).
    # None values are intentional: to_array() imputes via SPORT_MEDIANS.
    # ------------------------------------------------------------------

    def _team_form(self, home_team: str, away_team: str, sport: str) -> dict:
        """Query Supabase for last 10 game rolling stats.

        Returns empty dict on any error so to_array() handles imputation.
        """
        if self._db is None:
            return {}
        try:
            home_rows = (
                self._db.table("historical_games")
                .select("home_team,home_score,away_score,spread_result")
                .or_(f"home_team.eq.{home_team},away_team.eq.{home_team}")
                .order("game_date", desc=True)
                .limit(10)
                .execute()
            )
            away_rows = (
                self._db.table("historical_games")
                .select("home_team,home_score,away_score,spread_result")
                .or_(f"home_team.eq.{away_team},away_team.eq.{away_team}")
                .order("game_date", desc=True)
                .limit(10)
                .execute()
            )
            return compute_form_stats(
                home_team, home_rows.data or [], away_team, away_rows.data or []
            )
        except Exception:
            logger.debug("Failed to fetch team form for %s vs %s", home_team, away_team)
            return {}

    def _matchup_history(self, home_team: str, away_team: str, sport: str) -> dict:
        """Query Supabase H2H results and compute cover rate.

        Returns empty dict on any error.
        """
        if self._db is None:
            return {}
        try:
            rows = (
                self._db.table("historical_games")
                .select("home_team,spread_result")
                .or_(
                    f"and(home_team.eq.{home_team},away_team.eq.{away_team}),"
                    f"and(home_team.eq.{away_team},away_team.eq.{home_team})"
                )
                .execute()
            )
            data = rows.data or []
            if not data:
                return {}
            total = len(data)
            home_covers = sum(
                1
                for r in data
                if r.get("home_team") == home_team and r.get("spread_result") == "cover"
            )
            return {
                "h2h_home_cover_rate": home_covers / total if total > 0 else None,
                "h2h_total_games": total,
            }
        except Exception:
            logger.debug("Failed to fetch H2H for %s vs %s", home_team, away_team)
            return {}

    def _injury_impact(self, home_team: str, away_team: str, sport: str) -> tuple[float, float]:
        """Compute injury impact scores via ESPN scoreboard data.

        Returns (0.0, 0.0) when ESPN client is None or raises any exception.
        """
        if self._espn is None:
            return (0.0, 0.0)
        try:
            scoreboard = self._espn.get_scoreboard(sport=sport)
            return parse_injury_impact(scoreboard, home_team, away_team)
        except Exception:
            logger.debug("ESPN injury fetch failed for %s vs %s", home_team, away_team)
            return (0.0, 0.0)

    def _market_sentiment(self, game_context: dict) -> dict:
        """Extract line movement velocity and public betting percentage.

        line_movement_velocity: (last_line - first_line) / hours_elapsed
        public_pct_home: from PublicBettingClient if confidence >= 0.7.
        """
        result: dict = {}

        movements = game_context.get("line_movements", [])
        if len(movements) >= 2:
            try:
                first_line = float(movements[0]["line"])
                last_line = float(movements[-1]["line"])
                t_first = datetime.fromisoformat(movements[0]["timestamp"].replace("Z", "+00:00"))
                t_last = datetime.fromisoformat(movements[-1]["timestamp"].replace("Z", "+00:00"))
                hours_elapsed = (t_last - t_first).total_seconds() / 3600.0
                if hours_elapsed > 0:
                    result["line_movement_velocity"] = (last_line - first_line) / hours_elapsed
            except Exception:
                logger.debug("Failed to compute line movement velocity")

        if self._betting is not None:
            try:
                game_id = game_context.get("game_id", "")
                sport = game_context.get("sport", "")
                snapshot = sync_get_public_betting(self._betting, game_id, sport)
                if snapshot is not None and snapshot.confidence >= 0.7:
                    result["public_pct_home"] = snapshot.data.spread_ticket_home / 100.0
            except Exception:
                logger.debug("Failed to fetch public betting data")

        return result

    def _weather_travel(
        self, home_team: str, away_team: str, sport: str
    ) -> tuple[float | None, float]:
        """Compute weather impact score and travel penalty."""
        weather_score: float | None = None

        if self._weather is not None:
            try:
                weather_score = sync_get_weather_score(self._weather, home_team, sport)
            except Exception:
                logger.debug("Failed to fetch weather score for %s", home_team)

        crossings = compute_timezone_crossings(away_team, home_team)
        t_penalty = travel_penalty_from_crossings(crossings)

        return (weather_score, t_penalty)

    def _rest_days(
        self, home_team: str, away_team: str, sport: str, game_date: str
    ) -> tuple[int | None, int | None]:
        """Compute rest days for each team by querying last game before game_date."""
        if self._db is None or not game_date:
            return (None, None)
        try:
            home_rest = query_rest_days(self._db, home_team, game_date)
            away_rest = query_rest_days(self._db, away_team, game_date)
            return (home_rest, away_rest)
        except Exception:
            logger.debug("Failed to compute rest days for %s vs %s", home_team, away_team)
            return (None, None)
