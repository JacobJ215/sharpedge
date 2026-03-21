"""Middle opportunity detection.

A middle occurs when you can bet both sides of a spread/total
and potentially win BOTH bets if the result lands in the "middle."

Example:
    Book A: Team -2.5 (-110)
    Book B: Team +3.5 (-110)
    If team wins by exactly 3, you win BOTH bets.
"""

from dataclasses import dataclass

from scipy import stats


@dataclass
class MiddleResult:
    """Result of middle opportunity detection."""

    exists: bool  # True if middle opportunity exists
    side_a_line: float  # Line for side A (e.g., -2.5)
    side_b_line: float  # Line for side B (e.g., +3.5)
    middle_range: tuple[float, float]  # Range that wins both (e.g., 2.5 to 3.5)
    middle_width: float  # Width of middle (e.g., 1.0 point)
    hit_probability: float  # Estimated probability of hitting middle
    book_a: str
    book_b: str
    odds_a: int
    odds_b: int
    bet_type: str  # "spread" or "total"


# Standard deviation for score margins by sport
MARGIN_STDEV = {
    "NFL": 13.5,
    "NCAAF": 16.0,
    "NBA": 12.0,
    "NCAAB": 10.5,
    "MLB": 3.5,
    "NHL": 2.5,
}


def find_middle_opportunity(
    line_a: float,
    line_b: float,
    odds_a: int,
    odds_b: int,
    book_a: str = "Book A",
    book_b: str = "Book B",
    sport: str = "NFL",
    bet_type: str = "spread",
) -> MiddleResult:
    """Detect if a middle opportunity exists between two lines.

    For spreads: middle exists if favorite spread < underdog spread
    For totals: middle exists if under number < over number

    Args:
        line_a: Line from book A (e.g., -2.5 for favorite spread)
        line_b: Line from book B (e.g., +3.5 for underdog spread)
        odds_a: Odds at book A
        odds_b: Odds at book B
        book_a: Name of sportsbook A
        book_b: Name of sportsbook B
        sport: Sport for probability calculation
        bet_type: "spread" or "total"

    Returns:
        MiddleResult with opportunity details
    """
    # For spreads: line_a should be the favorite (negative), line_b the underdog (positive)
    # Middle exists if abs(line_a) < line_b
    # For totals: line_a is under, line_b is over - middle if line_a < line_b

    if bet_type == "spread":
        # Normalize: ensure we're comparing favorite spread to underdog spread
        fav_spread = min(line_a, line_b)  # More negative = bigger favorite
        dog_spread = max(line_a, line_b)  # More positive = bigger underdog

        # Middle exists if there's a gap
        # e.g., favorite -2.5 and underdog +3.5 = middle at 3
        middle_exists = abs(fav_spread) < dog_spread

        if middle_exists:
            middle_low = abs(fav_spread)
            middle_high = dog_spread
        else:
            middle_low = middle_high = 0
    else:
        # Totals: middle between under and over numbers
        under_line = min(line_a, line_b)
        over_line = max(line_a, line_b)

        middle_exists = under_line < over_line

        if middle_exists:
            middle_low = under_line
            middle_high = over_line
        else:
            middle_low = middle_high = 0

    if not middle_exists:
        return MiddleResult(
            exists=False,
            side_a_line=line_a,
            side_b_line=line_b,
            middle_range=(0, 0),
            middle_width=0,
            hit_probability=0,
            book_a=book_a,
            book_b=book_b,
            odds_a=odds_a,
            odds_b=odds_b,
            bet_type=bet_type,
        )

    middle_width = middle_high - middle_low
    hit_prob = calculate_middle_probability(middle_low, middle_high, sport, bet_type)

    return MiddleResult(
        exists=True,
        side_a_line=line_a,
        side_b_line=line_b,
        middle_range=(middle_low, middle_high),
        middle_width=round(middle_width, 1),
        hit_probability=round(hit_prob, 4),
        book_a=book_a,
        book_b=book_b,
        odds_a=odds_a,
        odds_b=odds_b,
        bet_type=bet_type,
    )


def calculate_middle_probability(
    low: float,
    high: float,
    sport: str = "NFL",
    bet_type: str = "spread",
) -> float:
    """Estimate probability of result landing in the middle.

    Uses normal distribution with sport-specific standard deviation.

    Args:
        low: Lower bound of middle
        high: Upper bound of middle
        sport: Sport for stdev lookup
        bet_type: "spread" or "total"

    Returns:
        Probability (0-1) of hitting the middle
    """
    stdev = MARGIN_STDEV.get(sport.upper(), 13.5)

    # For spreads, we're looking at margin relative to the spread
    # Assume mean is 0 (spread is "correct")
    if bet_type == "spread":
        # P(low < margin < high) using normal CDF
        prob = stats.norm.cdf(high, loc=0, scale=stdev) - stats.norm.cdf(low, loc=0, scale=stdev)
    else:
        # For totals, similar calculation but around the consensus total
        # This is simplified - in practice you'd want the actual total
        prob = stats.norm.cdf(high, loc=0, scale=stdev) - stats.norm.cdf(low, loc=0, scale=stdev)

    return max(0, min(1, prob))


def scan_for_middles(
    spreads_by_book: dict[str, tuple[float, int]],
    sport: str = "NFL",
) -> list[MiddleResult]:
    """Scan all book combinations for middle opportunities.

    Args:
        spreads_by_book: Dict mapping book to (spread, odds) for home team
        sport: Sport for probability calculation

    Returns:
        List of MiddleResult sorted by hit probability
    """
    opportunities = []
    books = list(spreads_by_book.keys())

    for i, book_a in enumerate(books):
        for book_b in books[i + 1 :]:
            line_a, odds_a = spreads_by_book[book_a]
            line_b, odds_b = spreads_by_book[book_b]

            # Check for middle in both directions
            result = find_middle_opportunity(
                line_a,
                -line_b,  # Opposite side
                odds_a,
                odds_b,
                book_a,
                book_b,
                sport,
                "spread",
            )
            if result.exists:
                opportunities.append(result)

    opportunities.sort(key=lambda x: x.hit_probability, reverse=True)
    return opportunities


def calculate_middle_ev(
    middle: MiddleResult,
    stake_per_side: float = 100,
) -> dict[str, float]:
    """Calculate expected value of a middle bet.

    Args:
        middle: MiddleResult from find_middle_opportunity
        stake_per_side: Amount to bet on each side

    Returns:
        Dict with EV, outcomes, and recommendations
    """
    if not middle.exists:
        return {"error": "No middle opportunity exists"}

    # Calculate outcomes
    total_stake = stake_per_side * 2

    # Win side A, lose side B
    def calc_profit(odds: int, stake: float) -> float:
        if odds > 0:
            return stake * (odds / 100)
        else:
            return stake * (100 / abs(odds))

    profit_a = calc_profit(middle.odds_a, stake_per_side) - stake_per_side
    profit_b = calc_profit(middle.odds_b, stake_per_side) - stake_per_side

    # Scenario outcomes
    win_a_lose_b = profit_a - stake_per_side  # Win A, lose B
    win_b_lose_a = profit_b - stake_per_side  # Win B, lose A
    win_both = profit_a + profit_b  # Hit the middle!

    # Expected value (simplified - assumes equal probability of each non-middle outcome)
    non_middle_prob = 1 - middle.hit_probability
    prob_each_side = non_middle_prob / 2

    ev = (
        prob_each_side * win_a_lose_b
        + prob_each_side * win_b_lose_a
        + middle.hit_probability * win_both
    )

    return {
        "total_stake": total_stake,
        "middle_hit_probability": middle.hit_probability,
        "if_hit_middle": round(win_both, 2),
        "if_side_a_wins": round(win_a_lose_b, 2),
        "if_side_b_wins": round(win_b_lose_a, 2),
        "expected_value": round(ev, 2),
        "ev_percentage": round((ev / total_stake) * 100, 2),
        "is_positive_ev": ev > 0,
    }
