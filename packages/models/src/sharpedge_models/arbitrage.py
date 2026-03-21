"""Arbitrage and middle detection module.

This module provides mathematical arbitrage detection across sportsbooks
and prediction markets. An arbitrage exists when the combined implied
probability of all outcomes is less than 100%.

Features:
- Two-way arbitrage (spread, total, moneyline)
- Three-way arbitrage (soccer, etc.)
- Middle opportunities (win both sides)
- Cross-platform arbitrage (sportsbook vs prediction market)
- Optimal stake calculation
- Fee-adjusted profit calculation

All calculations are pure mathematics - no ML required.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sharpedge_models.no_vig import american_to_decimal, american_to_implied


@dataclass
class ArbitrageOpportunity:
    """Represents a confirmed arbitrage opportunity."""

    game_id: str
    game_description: str
    market_type: str  # "spread", "total", "moneyline"
    sport: str

    # Side 1
    side1_book: str
    side1_selection: str  # "Chiefs -3.5" or "Over 45.5"
    side1_odds: int
    side1_implied: float

    # Side 2
    side2_book: str
    side2_selection: str
    side2_odds: int
    side2_implied: float

    # Arb metrics
    combined_implied: float  # Should be < 100% for arb
    profit_percentage: float  # Guaranteed profit %
    is_cross_platform: bool = False  # Sportsbook vs PM

    # Optimal stakes (for $100 total)
    stake1_percentage: float = 0.0
    stake2_percentage: float = 0.0

    # Timestamps
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None

    # Additional info
    notes: str = ""

    @property
    def is_valid(self) -> bool:
        """Check if this is a valid arbitrage (profit > 0)."""
        return self.profit_percentage > 0

    @property
    def edge_per_dollar(self) -> float:
        """Profit per dollar wagered."""
        return self.profit_percentage / 100


@dataclass
class MiddleOpportunity:
    """Represents a middle opportunity (chance to win both sides)."""

    game_id: str
    game_description: str
    market_type: str
    sport: str

    # Side 1
    side1_book: str
    side1_selection: str
    side1_line: float  # e.g., -3.5
    side1_odds: int

    # Side 2
    side2_book: str
    side2_selection: str
    side2_line: float  # e.g., +4.5
    side2_odds: int

    # Middle range
    middle_low: float  # If result lands between these
    middle_high: float  # ...you win both
    middle_width: float  # Points of cushion

    # Metrics
    probability_of_middle: float  # Estimated P(hitting middle)
    expected_value: float  # EV of the middle
    max_loss_percentage: float  # Worst case (both lose)
    max_win_percentage: float  # Best case (both win)

    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_profitable_ev(self) -> bool:
        """Check if this middle has positive expected value."""
        return self.expected_value > 0


# ============================================
# ARBITRAGE CALCULATION
# ============================================


def calculate_combined_implied(odds1: int, odds2: int) -> float:
    """Calculate combined implied probability for a two-way market.

    If this is < 100%, an arbitrage exists.
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)
    return (implied1 + implied2) * 100


def calculate_arb_profit(odds1: int, odds2: int) -> float:
    """Calculate arbitrage profit percentage.

    Returns profit as a percentage of total stake.
    E.g., 2.5 means 2.5% guaranteed profit.

    Returns negative if no arbitrage exists.
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    combined = implied1 + implied2

    if combined >= 1:
        # No arbitrage
        return -(combined - 1) * 100

    # Profit = 1 - combined implied
    # But we need to express as % of wagered amount
    profit = (1 / combined - 1) * 100

    return round(profit, 3)


def calculate_arb_stakes(
    odds1: int,
    odds2: int,
    total_stake: float = 100.0,
) -> tuple[float, float]:
    """Calculate optimal stakes for a two-way arbitrage.

    Returns the amount to bet on each side to guarantee
    equal profit regardless of outcome.

    Args:
        odds1: American odds for side 1
        odds2: American odds for side 2
        total_stake: Total amount to wager (default $100)

    Returns:
        Tuple of (stake1, stake2)
    """
    implied1 = american_to_implied(odds1)
    implied2 = american_to_implied(odds2)

    total_implied = implied1 + implied2

    # Stake proportional to implied probability
    stake1 = total_stake * (implied1 / total_implied)
    stake2 = total_stake * (implied2 / total_implied)

    return round(stake1, 2), round(stake2, 2)


def calculate_arb_payout(
    odds: int,
    stake: float,
) -> float:
    """Calculate total payout (stake + profit) if bet wins."""
    decimal = american_to_decimal(odds)
    return round(stake * decimal, 2)


def find_arbitrage(
    game_id: str,
    game_description: str,
    sport: str,
    market_type: str,
    book_odds: dict[str, tuple[int, int]],
    min_profit: float = 0.0,
    max_books: int | None = None,
) -> list[ArbitrageOpportunity]:
    """Find arbitrage opportunities across multiple books.

    Args:
        game_id: Unique game identifier
        game_description: Human-readable game description
        sport: Sport (NFL, NBA, etc.)
        market_type: Market type (spread, total, moneyline)
        book_odds: Dict of {book_name: (side1_odds, side2_odds)}
        min_profit: Minimum profit % to include (default 0 = all arbs)
        max_books: Maximum number of arbs to return

    Returns:
        List of ArbitrageOpportunity sorted by profit descending
    """
    if len(book_odds) < 2:
        return []

    opportunities = []

    # Find best odds for each side across all books
    books = list(book_odds.keys())

    for book1 in books:
        for book2 in books:
            if book1 == book2:
                continue

            # Take side 1 from book1, side 2 from book2
            side1_odds = book_odds[book1][0]
            side2_odds = book_odds[book2][1]

            profit = calculate_arb_profit(side1_odds, side2_odds)

            if profit > min_profit:
                combined = calculate_combined_implied(side1_odds, side2_odds)
                stake1_pct, stake2_pct = calculate_arb_stakes(side1_odds, side2_odds)

                opportunities.append(
                    ArbitrageOpportunity(
                        game_id=game_id,
                        game_description=game_description,
                        market_type=market_type,
                        sport=sport,
                        side1_book=book1,
                        side1_selection=f"Side 1 @ {book1}",
                        side1_odds=side1_odds,
                        side1_implied=american_to_implied(side1_odds) * 100,
                        side2_book=book2,
                        side2_selection=f"Side 2 @ {book2}",
                        side2_odds=side2_odds,
                        side2_implied=american_to_implied(side2_odds) * 100,
                        combined_implied=combined,
                        profit_percentage=profit,
                        stake1_percentage=stake1_pct,
                        stake2_percentage=stake2_pct,
                    )
                )

    # Sort by profit descending
    opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)

    # Remove duplicates (same pair, different order)
    seen = set()
    unique = []
    for opp in opportunities:
        key = frozenset(
            [
                (opp.side1_book, opp.side1_odds),
                (opp.side2_book, opp.side2_odds),
            ]
        )
        if key not in seen:
            seen.add(key)
            unique.append(opp)

    if max_books:
        unique = unique[:max_books]

    return unique


def find_best_arb(
    game_id: str,
    game_description: str,
    sport: str,
    market_type: str,
    book_odds: dict[str, tuple[int, int]],
) -> ArbitrageOpportunity | None:
    """Find the single best arbitrage opportunity.

    Optimized version that just finds best side1 and best side2 odds.
    """
    if len(book_odds) < 2:
        return None

    # Find best odds for each side
    best_side1 = max(book_odds.items(), key=lambda x: x[1][0])
    best_side2 = max(book_odds.items(), key=lambda x: x[1][1])

    # Can't arb with same book
    if best_side1[0] == best_side2[0]:
        # Find second best for one side
        other_books_side1 = {k: v for k, v in book_odds.items() if k != best_side2[0]}
        other_books_side2 = {k: v for k, v in book_odds.items() if k != best_side1[0]}

        if not other_books_side1 and not other_books_side2:
            return None

        # Try both options
        arbs = []

        if other_books_side1:
            alt_side1 = max(other_books_side1.items(), key=lambda x: x[1][0])
            profit1 = calculate_arb_profit(alt_side1[1][0], best_side2[1][1])
            if profit1 > 0:
                arbs.append((alt_side1, best_side2, profit1))

        if other_books_side2:
            alt_side2 = max(other_books_side2.items(), key=lambda x: x[1][1])
            profit2 = calculate_arb_profit(best_side1[1][0], alt_side2[1][1])
            if profit2 > 0:
                arbs.append((best_side1, alt_side2, profit2))

        if not arbs:
            return None

        # Use the better arb
        arbs.sort(key=lambda x: x[2], reverse=True)
        best_side1, best_side2, _ = arbs[0]

    side1_odds = best_side1[1][0]
    side2_odds = best_side2[1][1]

    profit = calculate_arb_profit(side1_odds, side2_odds)

    if profit <= 0:
        return None

    combined = calculate_combined_implied(side1_odds, side2_odds)
    stake1_pct, stake2_pct = calculate_arb_stakes(side1_odds, side2_odds)

    return ArbitrageOpportunity(
        game_id=game_id,
        game_description=game_description,
        market_type=market_type,
        sport=sport,
        side1_book=best_side1[0],
        side1_selection="Side 1",
        side1_odds=side1_odds,
        side1_implied=american_to_implied(side1_odds) * 100,
        side2_book=best_side2[0],
        side2_selection="Side 2",
        side2_odds=side2_odds,
        side2_implied=american_to_implied(side2_odds) * 100,
        combined_implied=combined,
        profit_percentage=profit,
        stake1_percentage=stake1_pct,
        stake2_percentage=stake2_pct,
    )


# ============================================
# MIDDLE DETECTION
# ============================================


def find_middles(
    game_id: str,
    game_description: str,
    sport: str,
    market_type: str,
    book_lines: dict[str, tuple[float, int, float, int]],
    min_width: float = 0.5,
    std_dev: float = 10.0,  # Score std dev for probability calc
) -> list[MiddleOpportunity]:
    """Find middle opportunities across books.

    A middle exists when you can bet both sides with different
    lines and potentially win both if the result lands between them.

    Args:
        game_id: Unique game identifier
        game_description: Human-readable description
        sport: Sport type
        market_type: spread or total
        book_lines: Dict of {book: (side1_line, side1_odds, side2_line, side2_odds)}
                   e.g., {"dk": (-3.5, -110, 3.5, -110), "fd": (-4.5, -110, 4.5, -110)}
        min_width: Minimum middle width in points
        std_dev: Standard deviation for probability estimation

    Returns:
        List of MiddleOpportunity sorted by expected value
    """
    if len(book_lines) < 2:
        return []

    opportunities = []
    books = list(book_lines.keys())

    for book1 in books:
        for book2 in books:
            if book1 == book2:
                continue

            line1_side1, odds1_side1, _line1_side2, _odds1_side2 = book_lines[book1]
            line2_side1, _odds2_side1, line2_side2, odds2_side2 = book_lines[book2]

            # Check for middle: bet side1 at book1, side2 at book2
            # For spreads: side1 is typically home spread, side2 is away
            # Middle exists if side1_line at book1 > side2_line at book2 (in absolute terms)

            if market_type == "spread":
                # Home spread at book1, away spread at book2
                # Middle if: home_spread + away_spread > 0
                # e.g., Home -3.5 at DK, Away +4.5 at FD = 1 point middle
                middle_width = abs(line1_side1) - abs(line2_side1)

                if middle_width >= min_width:
                    middle_low = min(abs(line1_side1), abs(line2_side1))
                    middle_high = max(abs(line1_side1), abs(line2_side1))

                    # Estimate probability of landing in middle
                    from scipy import stats

                    prob_middle = abs(
                        stats.norm.cdf(middle_high, 0, std_dev)
                        - stats.norm.cdf(middle_low, 0, std_dev)
                    )

                    # Calculate EV
                    decimal1 = american_to_decimal(odds1_side1)
                    decimal2 = american_to_decimal(odds2_side2)

                    # Assuming equal stakes
                    # Win both: profit = (decimal1 - 1) + (decimal2 - 1) per unit
                    # Win one: profit = (decimal - 1) - 1 = decimal - 2 per unit
                    # Lose both: profit = -2 per unit

                    win_both = (decimal1 - 1) + (decimal2 - 1)
                    win_one = (decimal1 + decimal2) / 2 - 2
                    lose_both = -2

                    # Approximate EV (simplified)
                    # P(middle) = prob_middle, P(one wins) = 1 - prob_middle
                    ev = prob_middle * win_both + (1 - prob_middle) * win_one

                    opportunities.append(
                        MiddleOpportunity(
                            game_id=game_id,
                            game_description=game_description,
                            market_type=market_type,
                            sport=sport,
                            side1_book=book1,
                            side1_selection=f"Home {line1_side1:+.1f}",
                            side1_line=line1_side1,
                            side1_odds=odds1_side1,
                            side2_book=book2,
                            side2_selection=f"Away {line2_side2:+.1f}",
                            side2_line=line2_side2,
                            side2_odds=odds2_side2,
                            middle_low=middle_low,
                            middle_high=middle_high,
                            middle_width=middle_width,
                            probability_of_middle=round(prob_middle * 100, 2),
                            expected_value=round(ev * 100, 2),
                            max_loss_percentage=round(lose_both * 50, 2),  # Per $100 total
                            max_win_percentage=round(win_both * 50, 2),
                        )
                    )

    # Sort by EV descending
    opportunities.sort(key=lambda x: x.expected_value, reverse=True)

    return opportunities


# ============================================
# CROSS-PLATFORM ARBITRAGE
# ============================================


def find_cross_platform_arb(
    event_description: str,
    sportsbook_odds: dict[str, int],  # {book: american_odds for YES}
    pm_odds: dict[str, float],  # {platform: implied_prob for YES}
    event_type: str = "binary",
) -> list[ArbitrageOpportunity]:
    """Find arbitrage between sportsbooks and prediction markets.

    Args:
        event_description: Description of the event
        sportsbook_odds: American odds from sportsbooks for the YES outcome
        pm_odds: Implied probability (0-1) from prediction markets for YES
        event_type: Type of event (binary, multi-way)

    Returns:
        List of cross-platform arbitrage opportunities
    """
    opportunities = []

    for sb_name, sb_odds in sportsbook_odds.items():
        sb_implied_yes = american_to_implied(sb_odds)
        1 - sb_implied_yes  # Simplified (ignoring vig on no side)

        for pm_name, pm_yes_prob in pm_odds.items():
            pm_no_prob = 1 - pm_yes_prob

            # Check arb: YES at sportsbook, NO at prediction market
            combined_yes_no = sb_implied_yes + pm_no_prob
            if combined_yes_no < 1:
                profit = (1 / combined_yes_no - 1) * 100
                opportunities.append(
                    ArbitrageOpportunity(
                        game_id=f"xp_{sb_name}_{pm_name}",
                        game_description=event_description,
                        market_type="binary",
                        sport="prediction_market",
                        side1_book=sb_name,
                        side1_selection="YES",
                        side1_odds=sb_odds,
                        side1_implied=sb_implied_yes * 100,
                        side2_book=pm_name,
                        side2_selection="NO",
                        side2_odds=implied_to_american_safe(pm_no_prob),
                        side2_implied=pm_no_prob * 100,
                        combined_implied=combined_yes_no * 100,
                        profit_percentage=round(profit, 3),
                        is_cross_platform=True,
                    )
                )

            # Check arb: NO at sportsbook (if available), YES at prediction market
            # This would require NO odds from sportsbook, which we don't have here

    opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
    return opportunities


def implied_to_american_safe(prob: float) -> int:
    """Safely convert implied probability to American odds."""
    if prob <= 0.01:
        return 9999
    if prob >= 0.99:
        return -9999

    if prob >= 0.5:
        return -round(prob / (1 - prob) * 100)
    else:
        return round((1 - prob) / prob * 100)


# ============================================
# FEE ADJUSTMENTS
# ============================================


@dataclass
class BookFees:
    """Fee structure for a sportsbook or platform."""

    name: str
    withdrawal_fee_pct: float = 0.0  # % fee on withdrawal
    deposit_fee_pct: float = 0.0  # % fee on deposit
    conversion_fee_pct: float = 0.0  # Crypto conversion fee (for PM)
    min_withdrawal: float = 0.0  # Minimum withdrawal amount


DEFAULT_FEES = {
    "draftkings": BookFees("draftkings"),
    "fanduel": BookFees("fanduel"),
    "betmgm": BookFees("betmgm"),
    "caesars": BookFees("caesars"),
    "pinnacle": BookFees("pinnacle"),
    "kalshi": BookFees("kalshi", withdrawal_fee_pct=0.0),
    "polymarket": BookFees("polymarket", conversion_fee_pct=1.0),  # Crypto fees
}


def adjust_profit_for_fees(
    profit_percentage: float,
    book1: str,
    book2: str,
    fees: dict[str, BookFees] | None = None,
) -> float:
    """Adjust arbitrage profit for platform fees.

    Args:
        profit_percentage: Raw profit percentage
        book1: Name of first book
        book2: Name of second book
        fees: Optional custom fee structure

    Returns:
        Fee-adjusted profit percentage
    """
    if fees is None:
        fees = DEFAULT_FEES

    total_fees = 0.0

    if book1.lower() in fees:
        book1_fees = fees[book1.lower()]
        total_fees += book1_fees.withdrawal_fee_pct
        total_fees += book1_fees.deposit_fee_pct
        total_fees += book1_fees.conversion_fee_pct

    if book2.lower() in fees:
        book2_fees = fees[book2.lower()]
        total_fees += book2_fees.withdrawal_fee_pct
        total_fees += book2_fees.deposit_fee_pct
        total_fees += book2_fees.conversion_fee_pct

    return round(profit_percentage - total_fees, 3)
