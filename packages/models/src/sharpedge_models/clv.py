"""Closing Line Value (CLV) calculation and portfolio tracking.

CLV measures whether a bet was placed at a better price than where
the market ultimately settled. Positive CLV indicates the bettor
consistently beat the closing line — the key marker of a sharp bettor.
"""

from dataclasses import dataclass

from sharpedge_models.ev_calculator import american_to_implied

__all__ = ["calculate_clv", "CLVStats", "aggregate_clv"]


def calculate_clv(bet_odds: int, closing_line_odds: int) -> float:
    """Calculate closing line value for a single bet.

    Positive CLV means the bet was placed at a better price than where
    the market closed (i.e., you beat the closing line).

    CLV = implied_prob(closing) - implied_prob(bet)

    A closing line that has moved against you (higher implied probability)
    means the market agreed with your view after you bet — a sign of edge.

    Args:
        bet_odds: American odds at the time of the bet (e.g., -110)
        closing_line_odds: American odds at market close (e.g., -120)

    Returns:
        CLV as a float. Positive = beat the close, negative = lost value.
    """
    bet_prob = american_to_implied(bet_odds)
    closing_prob = american_to_implied(closing_line_odds)
    return closing_prob - bet_prob


@dataclass
class CLVStats:
    """Running CLV statistics for a portfolio of bets."""

    n_bets: int
    total_clv: float
    running_average: float
    positive_clv_rate: float  # Fraction of bets with positive CLV


def aggregate_clv(clv_values: list[float]) -> CLVStats:
    """Aggregate a list of CLV values into portfolio CLV stats.

    Args:
        clv_values: List of CLV values, one per bet

    Returns:
        CLVStats with running average and positive CLV rate
    """
    if not clv_values:
        return CLVStats(
            n_bets=0,
            total_clv=0.0,
            running_average=0.0,
            positive_clv_rate=0.0,
        )

    n = len(clv_values)
    total = sum(clv_values)
    positive_rate = sum(1 for v in clv_values if v > 0) / n

    return CLVStats(
        n_bets=n,
        total_clv=total,
        running_average=total / n,
        positive_clv_rate=positive_rate,
    )
