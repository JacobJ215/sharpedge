"""No-vig (juice-free) odds calculation module.

This module provides mathematically accurate devigging of sportsbook odds
to determine true "fair" probabilities. This is the foundation for:
- +EV detection (compare book odds to fair odds)
- CLV calculation (compare bet odds to closing fair odds)
- Arbitrage detection (combined implied < 100%)

Methods implemented:
- Power method (industry standard for balanced markets)
- Multiplicative method (simple proportional removal)
- Additive method (splits vig equally)
- Shin method (accounts for favorite-longshot bias)

References:
- https://www.pinnacle.com/en/betting-resources/betting-tools/margin-calculator
- https://help.smarkets.com/hc/en-gb/articles/214554985-Removing-the-overround
"""

import math
from dataclasses import dataclass
from enum import Enum

from scipy.optimize import brentq


class DevigMethod(Enum):
    """Available devigging methods."""

    POWER = "power"  # Industry standard, best for balanced markets
    MULTIPLICATIVE = "multiplicative"  # Simple proportional
    ADDITIVE = "additive"  # Splits vig equally
    SHIN = "shin"  # Accounts for favorite-longshot bias
    WORST_CASE = "worst_case"  # Most conservative (lowest fair prob)


@dataclass
class NoVigResult:
    """Result of no-vig calculation for a two-way market."""

    fair_prob_side1: float  # True probability of side 1 (0-1)
    fair_prob_side2: float  # True probability of side 2 (0-1)
    fair_odds_side1: int  # Fair American odds for side 1
    fair_odds_side2: int  # Fair American odds for side 2
    vig_percentage: float  # Total vig/juice percentage
    method: str  # Method used for calculation

    @property
    def overround(self) -> float:
        """Total implied probability (should be ~100% after devig)."""
        return self.fair_prob_side1 + self.fair_prob_side2


@dataclass
class ThreeWayNoVigResult:
    """Result of no-vig calculation for a three-way market (e.g., soccer)."""

    fair_prob_1: float
    fair_prob_draw: float
    fair_prob_2: float
    fair_odds_1: int
    fair_odds_draw: int
    fair_odds_2: int
    vig_percentage: float
    method: str


# ============================================
# ODDS CONVERSION UTILITIES
# ============================================


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def implied_to_american(prob: float) -> int:
    """Convert implied probability to American odds."""
    if prob <= 0 or prob >= 1:
        raise ValueError(f"Probability must be between 0 and 1, got {prob}")

    odds = (
        -round(prob / (1 - prob) * 100)
        if prob >= 0.5
        else round((1 - prob) / prob * 100)
    )

    return odds


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds > 0:
        return 1 + odds / 100
    else:
        return 1 + 100 / abs(odds)


def decimal_to_american(decimal_odds: float) -> int:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return round((decimal_odds - 1) * 100)
    else:
        return round(-100 / (decimal_odds - 1))


# ============================================
# VIG CALCULATION
# ============================================


def calculate_vig(odds1: int, odds2: int) -> float:
    """Calculate the vig (juice/margin) percentage in a two-way market.

    Args:
        odds1: American odds for side 1
        odds2: American odds for side 2

    Returns:
        Vig as a percentage (e.g., 4.5 for 4.5% vig)
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total_implied = implied1 + implied2
    vig = (total_implied - 1) * 100

    return round(vig, 2)


def calculate_vig_three_way(odds1: int, odds_draw: int, odds2: int) -> float:
    """Calculate vig for a three-way market."""
    implied1 = american_to_implied(odds1)
    implied_draw = american_to_implied(odds_draw)
    implied2 = american_to_implied(odds2)

    total_implied = implied1 + implied_draw + implied2
    vig = (total_implied - 1) * 100

    return round(vig, 2)


# ============================================
# DEVIGGING METHODS
# ============================================


def devig_multiplicative(odds1: int, odds2: int) -> NoVigResult:
    """Remove vig using multiplicative (proportional) method.

    Simply scales down each probability proportionally so they sum to 100%.
    This is the simplest method but may not be the most accurate.

    Formula: fair_prob = implied_prob / sum(implied_probs)
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total = implied1 + implied2
    vig = (total - 1) * 100

    fair1 = implied1 / total
    fair2 = implied2 / total

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig, 2),
        method="multiplicative",
    )


def devig_additive(odds1: int, odds2: int) -> NoVigResult:
    """Remove vig using additive method.

    Subtracts half the vig from each side's implied probability.
    Simple but may produce negative probabilities for extreme odds.

    Formula: fair_prob = implied_prob - (overround / 2)
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total = implied1 + implied2
    vig = (total - 1) * 100
    vig_per_side = (total - 1) / 2

    fair1 = max(0.001, implied1 - vig_per_side)
    fair2 = max(0.001, implied2 - vig_per_side)

    # Normalize to sum to 1
    norm = fair1 + fair2
    fair1 /= norm
    fair2 /= norm

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig, 2),
        method="additive",
    )


def devig_power(odds1: int, odds2: int) -> NoVigResult:
    """Remove vig using the power method (industry standard).

    This is the most commonly used method by sharp bettors and is
    considered the industry standard for balanced two-way markets.

    It finds the exponent k such that: implied1^k + implied2^k = 1
    Then fair_prob = implied^k

    This method preserves the ratio of odds better than multiplicative.
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total = implied1 + implied2
    vig = (total - 1) * 100

    # If no vig, return as-is
    if abs(total - 1.0) < 0.0001:
        return NoVigResult(
            fair_prob_side1=round(implied1, 6),
            fair_prob_side2=round(implied2, 6),
            fair_odds_side1=odds1,
            fair_odds_side2=odds2,
            vig_percentage=0.0,
            method="power",
        )

    # Find k using numerical solver
    def objective(k: float) -> float:
        return implied1**k + implied2**k - 1

    try:
        # k is typically between 0 and 1 for markets with vig
        k = brentq(objective, 0.01, 0.999, xtol=1e-10)
    except ValueError:
        # Fallback to multiplicative if solver fails
        return devig_multiplicative(odds1, odds2)

    fair1 = implied1**k
    fair2 = implied2**k

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig, 2),
        method="power",
    )


def devig_shin(odds1: int, odds2: int) -> NoVigResult:
    """Remove vig using Shin's method.

    Accounts for the favorite-longshot bias by assuming the overround
    is caused by informed bettors. Better for markets with significant
    odds discrepancy.

    Reference: Shin, H. S. (1993). Measuring the Incidence of Insider Trading
    in a Market for State-Contingent Claims.
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total = implied1 + implied2
    vig = (total - 1) * 100

    # Shin's method finds z such that:
    # sum of (sqrt(z^2 + 4*(1-z)*implied^2) - z) / (2*(1-z)) = 1

    def shin_fair(implied: float, z: float) -> float:
        """Calculate fair probability using Shin's formula."""
        return (math.sqrt(z**2 + 4 * (1 - z) * implied**2) - z) / (2 * (1 - z))

    def objective(z: float) -> float:
        return shin_fair(implied1, z) + shin_fair(implied2, z) - 1

    try:
        z = brentq(objective, 0.001, 0.5, xtol=1e-10)
        fair1 = shin_fair(implied1, z)
        fair2 = shin_fair(implied2, z)
    except (ValueError, ZeroDivisionError):
        # Fallback to power method
        return devig_power(odds1, odds2)

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig, 2),
        method="shin",
    )


def devig_worst_case(odds1: int, odds2: int) -> NoVigResult:
    """Most conservative devig - assumes all vig is against you.

    For each side, assumes the fair probability is just the implied
    probability. This is the "worst case" - if you're betting side 1,
    you assume all the vig was added to side 1's implied probability.

    Returns: The lower fair probability for each side.
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total = implied1 + implied2
    vig = (total - 1) * 100

    # For each side, assume the other side has no vig
    fair1 = 1 - implied2  # If side2 is accurate, side1 is remainder
    fair2 = 1 - implied1  # If side1 is accurate, side2 is remainder

    # Ensure valid range
    fair1 = max(0.01, min(0.99, fair1))
    fair2 = max(0.01, min(0.99, fair2))

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig, 2),
        method="worst_case",
    )


# ============================================
# MAIN API
# ============================================


def calculate_no_vig(
    odds1: int,
    odds2: int,
    method: DevigMethod = DevigMethod.POWER,
) -> NoVigResult:
    """Calculate fair (no-vig) probabilities and odds.

    This is the main function for devigging a two-way market.

    Args:
        odds1: American odds for side 1 (e.g., home team spread)
        odds2: American odds for side 2 (e.g., away team spread)
        method: Devigging method to use (default: POWER)

    Returns:
        NoVigResult with fair probabilities and odds

    Example:
        >>> result = calculate_no_vig(-110, -110)
        >>> print(result.fair_prob_side1)  # 0.5
        >>> print(result.vig_percentage)   # ~4.5%

        >>> result = calculate_no_vig(-150, +130)
        >>> print(result.fair_prob_side1)  # ~0.57 (favorite's true prob)
    """
    if method == DevigMethod.POWER:
        return devig_power(odds1, odds2)
    elif method == DevigMethod.MULTIPLICATIVE:
        return devig_multiplicative(odds1, odds2)
    elif method == DevigMethod.ADDITIVE:
        return devig_additive(odds1, odds2)
    elif method == DevigMethod.SHIN:
        return devig_shin(odds1, odds2)
    elif method == DevigMethod.WORST_CASE:
        return devig_worst_case(odds1, odds2)
    else:
        raise ValueError(f"Unknown devig method: {method}")


def calculate_fair_line(
    home_spread: float,
    home_odds: int,
    away_odds: int,
    method: DevigMethod = DevigMethod.POWER,
) -> tuple[float, float]:
    """Calculate the fair spread line given current odds.

    If a book is offering Home -3.5 at -110/-110, the fair line is -3.5.
    But if it's -3.5 at -120/+100, the market suggests the fair line
    is slightly different.

    Args:
        home_spread: Current spread (e.g., -3.5 means home favored by 3.5)
        home_odds: American odds on home spread
        away_odds: American odds on away spread

    Returns:
        Tuple of (fair_spread, fair_probability_home_covers)
    """
    result = calculate_no_vig(home_odds, away_odds, method)

    # The fair spread is approximately the current spread adjusted by
    # the probability imbalance. This is a simplified approximation.
    # A more accurate method would use a normal distribution model.

    # If fair prob is 50/50, current spread is fair
    # If fair prob is 55/45, spread should be ~0.5 points more favorable
    prob_diff = result.fair_prob_side1 - 0.5

    # Approximate: 2.5% prob = 0.5 points of spread in NFL
    # This varies by sport, but is a reasonable default
    spread_adjustment = prob_diff * 20  # ~0.5 pts per 2.5% prob

    fair_spread = home_spread - spread_adjustment

    return round(fair_spread, 1), result.fair_prob_side1


def calculate_fair_total(
    total_line: float,
    over_odds: int,
    under_odds: int,
    method: DevigMethod = DevigMethod.POWER,
) -> tuple[float, float]:
    """Calculate the fair total line given current odds.

    Args:
        total_line: Current total line (e.g., 45.5)
        over_odds: American odds on over
        under_odds: American odds on under

    Returns:
        Tuple of (fair_total, fair_probability_over)
    """
    result = calculate_no_vig(over_odds, under_odds, method)

    prob_diff = result.fair_prob_side1 - 0.5
    total_adjustment = prob_diff * 20

    fair_total = total_line - total_adjustment

    return round(fair_total, 1), result.fair_prob_side1


def calculate_ev(
    bet_odds: int,
    fair_prob: float,
) -> float:
    """Calculate expected value percentage for a bet.

    Args:
        bet_odds: American odds you're getting
        fair_prob: True probability of winning (0-1)

    Returns:
        EV as a percentage (e.g., 5.0 means +5% EV)
    """
    decimal_odds = american_to_decimal(bet_odds)

    # EV = (prob * payout) - (1 - prob) * stake
    # = (prob * (decimal - 1)) - (1 - prob)
    # = prob * decimal - prob - 1 + prob
    # = prob * decimal - 1
    ev = fair_prob * decimal_odds - 1

    return round(ev * 100, 2)


def find_ev_opportunities(
    market_odds: dict[str, tuple[int, int]],
    min_ev: float = 1.0,
    method: DevigMethod = DevigMethod.POWER,
) -> list[dict]:
    """Find +EV opportunities across multiple books.

    Args:
        market_odds: Dict of {book_name: (side1_odds, side2_odds)}
        min_ev: Minimum EV% to include (default 1%)
        method: Devigging method to use

    Returns:
        List of +EV opportunities with details

    Example:
        >>> odds = {
        ...     "pinnacle": (-108, -108),
        ...     "draftkings": (-110, -110),
        ...     "fanduel": (-115, -105),
        ... }
        >>> opportunities = find_ev_opportunities(odds)
    """
    if not market_odds:
        return []

    # Use Pinnacle or consensus for fair odds (they have lowest vig)
    if "pinnacle" in market_odds:
        reference = market_odds["pinnacle"]
    else:
        # Use the book with lowest vig as reference
        lowest_vig_book = min(
            market_odds.keys(), key=lambda b: calculate_vig(market_odds[b][0], market_odds[b][1])
        )
        reference = market_odds[lowest_vig_book]

    fair = calculate_no_vig(reference[0], reference[1], method)

    opportunities = []

    for book, (odds1, odds2) in market_odds.items():
        # Check side 1
        ev1 = calculate_ev(odds1, fair.fair_prob_side1)
        if ev1 >= min_ev:
            opportunities.append(
                {
                    "book": book,
                    "side": "side1",
                    "odds": odds1,
                    "fair_prob": fair.fair_prob_side1,
                    "fair_odds": fair.fair_odds_side1,
                    "ev_percentage": ev1,
                }
            )

        # Check side 2
        ev2 = calculate_ev(odds2, fair.fair_prob_side2)
        if ev2 >= min_ev:
            opportunities.append(
                {
                    "book": book,
                    "side": "side2",
                    "odds": odds2,
                    "fair_prob": fair.fair_prob_side2,
                    "fair_odds": fair.fair_odds_side2,
                    "ev_percentage": ev2,
                }
            )

    # Sort by EV descending
    opportunities.sort(key=lambda x: x["ev_percentage"], reverse=True)

    return opportunities


def calculate_consensus_fair_odds(
    all_book_odds: list[tuple[int, int]],
    weights: list[float] | None = None,
) -> NoVigResult:
    """Calculate consensus fair odds from multiple books.

    Uses weighted average of devigged probabilities from each book.
    This is more robust than using a single book.

    Args:
        all_book_odds: List of (side1_odds, side2_odds) for each book
        weights: Optional weights for each book (defaults to equal)

    Returns:
        NoVigResult with consensus fair probabilities
    """
    if not all_book_odds:
        raise ValueError("At least one book's odds required")

    if weights is None:
        weights = [1.0] * len(all_book_odds)

    if len(weights) != len(all_book_odds):
        raise ValueError("Weights must match number of books")

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Calculate weighted average of fair probabilities
    fair_prob1_sum = 0.0
    fair_prob2_sum = 0.0
    vig_sum = 0.0

    for (odds1, odds2), weight in zip(all_book_odds, weights, strict=False):
        result = devig_power(odds1, odds2)
        fair_prob1_sum += result.fair_prob_side1 * weight
        fair_prob2_sum += result.fair_prob_side2 * weight
        vig_sum += result.vig_percentage * weight

    # Normalize to ensure sum = 1
    total = fair_prob1_sum + fair_prob2_sum
    fair1 = fair_prob1_sum / total
    fair2 = fair_prob2_sum / total

    return NoVigResult(
        fair_prob_side1=round(fair1, 6),
        fair_prob_side2=round(fair2, 6),
        fair_odds_side1=implied_to_american(fair1),
        fair_odds_side2=implied_to_american(fair2),
        vig_percentage=round(vig_sum, 2),
        method="consensus",
    )


# ============================================
# N-OUTCOME SHIN DEVIG
# ============================================


def devig_shin_n_outcome(implied_probs: list[float]) -> list[float]:
    """N-outcome Shin devig. Generalizes devig_shin() to N>=2 outcomes.

    Algorithm: find z in (0, 1) such that sum(shin_fair(q_i, z)) == 1.0
    where shin_fair(q, z) = (sqrt(z**2 + 4*(1-z)*q**2) - z) / (2*(1-z))

    Reference: Shin (1993); mberk/shin on GitHub for N-outcome formulation.
    Uses scipy.optimize.brentq — already a workspace dependency in sharpedge-models.

    Returns:
        list[float]: fair probabilities summing to 1.0, all in (0, 1).

    Raises:
        ValueError: if implied_probs is empty or contains values outside (0, 1).
    """
    if not implied_probs:
        raise ValueError("implied_probs must not be empty")
    for p in implied_probs:
        if not (0.0 < p < 1.0):
            raise ValueError(f"All implied probs must be in (0, 1), got {p}")

    total = sum(implied_probs)
    if abs(total - 1.0) < 1e-6:
        # Already sums to 1 — no vig detected, return as-is
        return list(implied_probs)

    def shin_fair(q: float, z: float) -> float:
        return (math.sqrt(z**2 + 4.0 * (1.0 - z) * q**2) - z) / (2.0 * (1.0 - z))

    def objective(z: float) -> float:
        return sum(shin_fair(q, z) for q in implied_probs) - 1.0

    try:
        z = brentq(objective, 1e-9, 1.0 - 1e-9, xtol=1e-10)
        fair = [shin_fair(q, z) for q in implied_probs]
        # Normalize for floating-point safety
        s = sum(fair)
        return [p / s for p in fair]
    except ValueError:
        # Fallback: multiplicative normalization (always valid)
        return [q / total for q in implied_probs]
