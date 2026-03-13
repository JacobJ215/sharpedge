"""No-vig (fair) odds calculations.

The vig (vigorish/juice) is the bookmaker's margin built into the odds.
Removing it reveals the "true" market probability.

Example:
    Standard -110/-110 implies 52.38% + 52.38% = 104.76% (4.76% vig)
    True probability is 50/50, fair odds would be +100/+100
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class NoVigResult:
    """Result of no-vig calculation."""

    fair_prob_a: float  # True probability side A (0-1)
    fair_prob_b: float  # True probability side B (0-1)
    fair_odds_a: int  # Fair American odds side A
    fair_odds_b: int  # Fair American odds side B
    vig_percentage: float  # Bookmaker's margin as percentage
    market_odds_a: int  # Original odds side A
    market_odds_b: int  # Original odds side B


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def prob_to_american(prob: float) -> int:
    """Convert probability to American odds."""
    if prob <= 0 or prob >= 1:
        raise ValueError("Probability must be between 0 and 1 exclusive")

    if prob >= 0.5:
        # Favorite: negative odds
        return round(-100 * prob / (1 - prob))
    else:
        # Underdog: positive odds
        return round(100 * (1 - prob) / prob)


def calculate_vig_percentage(odds_a: int, odds_b: int) -> float:
    """Calculate the vig (overround) as a percentage.

    Args:
        odds_a: American odds for side A
        odds_b: American odds for side B

    Returns:
        Vig as percentage (e.g., 4.76 for standard -110/-110)
    """
    implied_a = american_to_implied_prob(odds_a)
    implied_b = american_to_implied_prob(odds_b)
    total = implied_a + implied_b
    return (total - 1) * 100


def calculate_no_vig_odds(odds_a: int, odds_b: int) -> tuple[float, float]:
    """Calculate true (no-vig) probabilities for both sides.

    Args:
        odds_a: American odds for side A (e.g., home team)
        odds_b: American odds for side B (e.g., away team)

    Returns:
        Tuple of (fair_prob_a, fair_prob_b) summing to 1.0
    """
    implied_a = american_to_implied_prob(odds_a)
    implied_b = american_to_implied_prob(odds_b)
    total = implied_a + implied_b

    fair_prob_a = implied_a / total
    fair_prob_b = implied_b / total

    return fair_prob_a, fair_prob_b


def calculate_fair_odds(odds_a: int, odds_b: int) -> NoVigResult:
    """Calculate complete no-vig analysis.

    Args:
        odds_a: American odds for side A
        odds_b: American odds for side B

    Returns:
        NoVigResult with fair probabilities, fair odds, and vig percentage
    """
    fair_prob_a, fair_prob_b = calculate_no_vig_odds(odds_a, odds_b)
    vig = calculate_vig_percentage(odds_a, odds_b)

    fair_odds_a = prob_to_american(fair_prob_a)
    fair_odds_b = prob_to_american(fair_prob_b)

    return NoVigResult(
        fair_prob_a=round(fair_prob_a, 4),
        fair_prob_b=round(fair_prob_b, 4),
        fair_odds_a=fair_odds_a,
        fair_odds_b=fair_odds_b,
        vig_percentage=round(vig, 2),
        market_odds_a=odds_a,
        market_odds_b=odds_b,
    )


def calculate_edge(model_prob: float, market_odds: int) -> float:
    """Calculate edge given model probability and market odds.

    Args:
        model_prob: Your estimated probability (0-1)
        market_odds: Current American odds

    Returns:
        Edge as percentage points (e.g., 3.5 means 3.5% edge)
    """
    implied_prob = american_to_implied_prob(market_odds)
    return (model_prob - implied_prob) * 100


def calculate_expected_value(model_prob: float, market_odds: int) -> float:
    """Calculate expected value of a bet.

    Args:
        model_prob: Your estimated probability of winning (0-1)
        market_odds: Current American odds

    Returns:
        EV as percentage of stake (e.g., 5.0 means +5% EV)
    """
    if market_odds > 0:
        decimal_odds = (market_odds / 100) + 1
    else:
        decimal_odds = (100 / abs(market_odds)) + 1

    ev = (model_prob * decimal_odds) - 1
    return ev * 100


def find_best_odds_value(
    fair_prob: float, odds_by_book: dict[str, int]
) -> dict[str, float]:
    """Find the EV at each sportsbook given fair probability.

    Args:
        fair_prob: True probability from no-vig calculation
        odds_by_book: Dict mapping sportsbook name to American odds

    Returns:
        Dict mapping sportsbook name to EV percentage
    """
    return {
        book: calculate_expected_value(fair_prob, odds)
        for book, odds in odds_by_book.items()
    }
