"""Total points prediction model."""

import logging
from dataclasses import dataclass

logger = logging.getLogger("sharpedge.models.totals")


@dataclass
class TotalProjection:
    projected_total: float
    confidence: float
    home_points: float
    away_points: float
    home_team: str
    away_team: str


class TotalsModel:
    """Simple totals projection model based on team pace and efficiency.

    For MVP, uses team offensive/defensive ratings to project total points.
    """

    def __init__(self) -> None:
        self._ratings: dict[str, dict[str, float]] = {}

    def set_team_ratings(self, ratings: dict[str, dict[str, float]]) -> None:
        """Set team ratings with 'offense' and 'defense' keys."""
        self._ratings = ratings

    def predict(
        self,
        home_team: str,
        away_team: str,
        venue_indoor: bool = False,
        wind_mph: float = 0,
        temp_f: float = 65,
    ) -> TotalProjection:
        """Predict total points for a game."""
        home_ratings = self._ratings.get(home_team, {"offense": 0.0, "defense": 0.0})
        away_ratings = self._ratings.get(away_team, {"offense": 0.0, "defense": 0.0})

        baseline_ppg = 22.0  # NFL average

        home_score = baseline_ppg + home_ratings["offense"] - away_ratings["defense"] + 2.5
        away_score = baseline_ppg + away_ratings["offense"] - home_ratings["defense"]

        total = home_score + away_score

        # Weather adjustments for outdoor games
        if not venue_indoor:
            if wind_mph > 15:
                total -= 2.0  # High wind reduces scoring
            if temp_f < 32:
                total -= 1.5  # Extreme cold reduces scoring
            elif temp_f > 90:
                total -= 0.5  # Extreme heat slight impact

        # Confidence (typical SD for NFL totals ~10 points)
        confidence = 10.0

        return TotalProjection(
            projected_total=round(total, 1),
            confidence=round(confidence, 1),
            home_points=round(home_score, 1),
            away_points=round(away_score, 1),
            home_team=home_team,
            away_team=away_team,
        )
