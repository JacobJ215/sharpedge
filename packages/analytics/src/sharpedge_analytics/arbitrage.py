"""Arbitrage detection and calculation.

Arbitrage occurs when the combined implied probabilities across
two sportsbooks sum to less than 100%, guaranteeing profit.

Example:
    Book A: Team A +150 (40% implied)
    Book B: Team B -130 (56.5% implied)
    Total: 96.5% = 3.5% guaranteed profit

Enhanced with sportsbook fee accounting for accurate net profit calculation.
"""

from dataclasses import dataclass, field


# ============================================
# SPORTSBOOK FEE STRUCTURES
# Account for withdrawal fees, limits, etc.
# ============================================
@dataclass
class SportsbookFees:
    """Fee structure for a sportsbook."""

    name: str
    withdrawal_fee: float = 0.0  # Fixed fee per withdrawal
    withdrawal_pct: float = 0.0  # Percentage fee on withdrawal
    min_withdrawal: float = 10.0  # Minimum withdrawal amount
    max_payout_per_bet: float = 100000.0  # Maximum payout limit
    verification_friction: float = 0.0  # Est. friction (0-1) for verification


# Common sportsbook fee configurations
SPORTSBOOK_FEES: dict[str, SportsbookFees] = {
    "fanduel": SportsbookFees(
        name="FanDuel",
        withdrawal_fee=0.0,
        min_withdrawal=10.0,
        max_payout_per_bet=1000000.0,
    ),
    "draftkings": SportsbookFees(
        name="DraftKings",
        withdrawal_fee=0.0,
        min_withdrawal=20.0,
        max_payout_per_bet=500000.0,
    ),
    "betmgm": SportsbookFees(
        name="BetMGM",
        withdrawal_fee=0.0,
        min_withdrawal=20.0,
        max_payout_per_bet=500000.0,
    ),
    "caesars": SportsbookFees(
        name="Caesars",
        withdrawal_fee=0.0,
        min_withdrawal=20.0,
        max_payout_per_bet=500000.0,
    ),
    "pointsbet": SportsbookFees(
        name="PointsBet",
        withdrawal_fee=0.0,
        min_withdrawal=50.0,
        max_payout_per_bet=250000.0,
    ),
    "betonline": SportsbookFees(
        name="BetOnline",
        withdrawal_fee=0.0,
        withdrawal_pct=0.03,  # 3% on some methods
        min_withdrawal=50.0,
        max_payout_per_bet=100000.0,
        verification_friction=0.2,  # Offshore, more friction
    ),
    "bovada": SportsbookFees(
        name="Bovada",
        withdrawal_fee=0.0,
        withdrawal_pct=0.0,
        min_withdrawal=10.0,
        max_payout_per_bet=250000.0,
        verification_friction=0.15,
    ),
    "pinnacle": SportsbookFees(
        name="Pinnacle",
        withdrawal_fee=0.0,
        min_withdrawal=20.0,
        max_payout_per_bet=500000.0,
        verification_friction=0.1,
    ),
}


def get_sportsbook_fees(book_key: str) -> SportsbookFees:
    """Get fee structure for a sportsbook."""
    return SPORTSBOOK_FEES.get(
        book_key.lower(),
        SportsbookFees(name=book_key),  # Default: no fees
    )


@dataclass
class ArbitrageResult:
    """Result of arbitrage detection."""

    exists: bool  # True if arbitrage opportunity exists
    profit_percentage: float  # Guaranteed profit as percentage
    stake_a_percentage: float  # Percentage of total stake on side A
    stake_b_percentage: float  # Percentage of total stake on side B
    odds_a: int  # Odds for side A
    odds_b: int  # Odds for side B
    book_a: str  # Sportsbook for side A
    book_b: str  # Sportsbook for side B
    total_implied: float  # Combined implied probability


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds > 0:
        return (odds / 100) + 1
    else:
        return (100 / abs(odds)) + 1


def american_to_implied_prob(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def find_arbitrage(
    odds_a: int,
    odds_b: int,
    book_a: str = "Book A",
    book_b: str = "Book B",
) -> ArbitrageResult:
    """Check if arbitrage exists between two odds.

    Args:
        odds_a: American odds for side A (e.g., home team)
        odds_b: American odds for side B (e.g., away team)
        book_a: Name of sportsbook offering odds_a
        book_b: Name of sportsbook offering odds_b

    Returns:
        ArbitrageResult with profit and stake info if arb exists
    """
    implied_a = american_to_implied_prob(odds_a)
    implied_b = american_to_implied_prob(odds_b)
    total_implied = implied_a + implied_b

    if total_implied >= 1.0:
        # No arbitrage - combined probability >= 100%
        return ArbitrageResult(
            exists=False,
            profit_percentage=0,
            stake_a_percentage=0,
            stake_b_percentage=0,
            odds_a=odds_a,
            odds_b=odds_b,
            book_a=book_a,
            book_b=book_b,
            total_implied=round(total_implied, 4),
        )

    # Arbitrage exists
    profit_pct = (1 / total_implied - 1) * 100

    # Calculate optimal stakes
    stake_a_pct = (implied_a / total_implied) * 100
    stake_b_pct = (implied_b / total_implied) * 100

    return ArbitrageResult(
        exists=True,
        profit_percentage=round(profit_pct, 2),
        stake_a_percentage=round(stake_a_pct, 2),
        stake_b_percentage=round(stake_b_pct, 2),
        odds_a=odds_a,
        odds_b=odds_b,
        book_a=book_a,
        book_b=book_b,
        total_implied=round(total_implied, 4),
    )


def calculate_arbitrage_stakes(
    total_stake: float,
    odds_a: int,
    odds_b: int,
) -> dict[str, float]:
    """Calculate exact dollar stakes for arbitrage bet.

    Args:
        total_stake: Total amount to wager (across both sides)
        odds_a: American odds for side A
        odds_b: American odds for side B

    Returns:
        Dict with stake_a, stake_b, guaranteed_profit, roi
    """
    arb = find_arbitrage(odds_a, odds_b)

    if not arb.exists:
        return {
            "stake_a": 0,
            "stake_b": 0,
            "guaranteed_profit": 0,
            "roi": 0,
            "error": "No arbitrage opportunity exists",
        }

    stake_a = total_stake * (arb.stake_a_percentage / 100)
    stake_b = total_stake * (arb.stake_b_percentage / 100)

    # Calculate guaranteed return
    decimal_a = american_to_decimal(odds_a)
    decimal_b = american_to_decimal(odds_b)

    return_if_a_wins = stake_a * decimal_a
    return_if_b_wins = stake_b * decimal_b

    # Both should be equal (that's the arbitrage)
    guaranteed_return = min(return_if_a_wins, return_if_b_wins)
    guaranteed_profit = guaranteed_return - total_stake

    return {
        "stake_a": round(stake_a, 2),
        "stake_b": round(stake_b, 2),
        "guaranteed_profit": round(guaranteed_profit, 2),
        "roi": round(arb.profit_percentage, 2),
        "return_if_a_wins": round(return_if_a_wins, 2),
        "return_if_b_wins": round(return_if_b_wins, 2),
    }


def scan_for_arbitrage(
    odds_by_book_side_a: dict[str, int],
    odds_by_book_side_b: dict[str, int],
) -> list[ArbitrageResult]:
    """Scan all book combinations for arbitrage opportunities.

    Args:
        odds_by_book_side_a: Dict mapping book name to odds for side A
        odds_by_book_side_b: Dict mapping book name to odds for side B

    Returns:
        List of ArbitrageResult for all arb opportunities found, sorted by profit
    """
    opportunities = []

    for book_a, odds_a in odds_by_book_side_a.items():
        for book_b, odds_b in odds_by_book_side_b.items():
            # Skip same book (can't arb yourself)
            if book_a.lower() == book_b.lower():
                continue

            result = find_arbitrage(odds_a, odds_b, book_a, book_b)
            if result.exists:
                opportunities.append(result)

    # Sort by profit percentage descending
    opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)
    return opportunities


def find_best_arb_combo(
    odds_by_book_side_a: dict[str, int],
    odds_by_book_side_b: dict[str, int],
) -> ArbitrageResult | None:
    """Find the single best arbitrage opportunity.

    Args:
        odds_by_book_side_a: Dict mapping book name to odds for side A
        odds_by_book_side_b: Dict mapping book name to odds for side B

    Returns:
        Best ArbitrageResult or None if no arb exists
    """
    opportunities = scan_for_arbitrage(odds_by_book_side_a, odds_by_book_side_b)
    return opportunities[0] if opportunities else None


@dataclass
class FeeAdjustedArbitrage:
    """Arbitrage result with fee accounting."""

    exists: bool
    gross_profit_pct: float  # Before fees
    net_profit_pct: float  # After fees
    fee_cost: float  # Total fee impact
    stake_a: float
    stake_b: float
    guaranteed_return: float
    net_profit: float
    book_a: str
    book_b: str
    odds_a: int
    odds_b: int
    book_a_fees: SportsbookFees | None = None
    book_b_fees: SportsbookFees | None = None


def find_arbitrage_with_fees(
    odds_a: int,
    odds_b: int,
    book_a: str,
    book_b: str,
    total_stake: float = 1000.0,
) -> FeeAdjustedArbitrage:
    """Find arbitrage with sportsbook fee accounting.

    This provides a more accurate picture of net profit by
    accounting for withdrawal fees, limits, and friction.

    Args:
        odds_a: American odds for side A
        odds_b: American odds for side B
        book_a: Sportsbook key for side A
        book_b: Sportsbook key for side B
        total_stake: Total amount to wager

    Returns:
        FeeAdjustedArbitrage with gross and net profit
    """
    # Get fee structures
    fees_a = get_sportsbook_fees(book_a)
    fees_b = get_sportsbook_fees(book_b)

    # Basic arb check
    basic_arb = find_arbitrage(odds_a, odds_b, book_a, book_b)

    if not basic_arb.exists:
        return FeeAdjustedArbitrage(
            exists=False,
            gross_profit_pct=0,
            net_profit_pct=0,
            fee_cost=0,
            stake_a=0,
            stake_b=0,
            guaranteed_return=0,
            net_profit=0,
            book_a=book_a,
            book_b=book_b,
            odds_a=odds_a,
            odds_b=odds_b,
            book_a_fees=fees_a,
            book_b_fees=fees_b,
        )

    # Calculate stakes
    stakes = calculate_arbitrage_stakes(total_stake, odds_a, odds_b)
    stake_a = stakes["stake_a"]
    stake_b = stakes["stake_b"]
    gross_profit = stakes["guaranteed_profit"]

    # Calculate fees on winnings
    # Assume we need to withdraw from winning book
    # Worst case: pay fees on both withdrawals
    fee_a = fees_a.withdrawal_fee + (gross_profit * fees_a.withdrawal_pct)
    fee_b = fees_b.withdrawal_fee + (gross_profit * fees_b.withdrawal_pct)

    # Average expected fee (we only withdraw from winner, but don't know which)
    expected_fee = (fee_a + fee_b) / 2

    net_profit = gross_profit - expected_fee
    net_profit_pct = (net_profit / total_stake) * 100 if total_stake > 0 else 0

    return FeeAdjustedArbitrage(
        exists=net_profit > 0,
        gross_profit_pct=basic_arb.profit_percentage,
        net_profit_pct=round(net_profit_pct, 2),
        fee_cost=round(expected_fee, 2),
        stake_a=stake_a,
        stake_b=stake_b,
        guaranteed_return=round(stakes.get("return_if_a_wins", total_stake), 2),
        net_profit=round(net_profit, 2),
        book_a=book_a,
        book_b=book_b,
        odds_a=odds_a,
        odds_b=odds_b,
        book_a_fees=fees_a,
        book_b_fees=fees_b,
    )


def scan_for_arbitrage_with_fees(
    odds_by_book_side_a: dict[str, int],
    odds_by_book_side_b: dict[str, int],
    total_stake: float = 1000.0,
    min_net_profit_pct: float = 0.5,
) -> list[FeeAdjustedArbitrage]:
    """Scan for arbitrage with fee accounting.

    Args:
        odds_by_book_side_a: Dict mapping book name to odds for side A
        odds_by_book_side_b: Dict mapping book name to odds for side B
        total_stake: Total amount to wager per arb
        min_net_profit_pct: Minimum net profit to include

    Returns:
        List of fee-adjusted arbitrage opportunities, sorted by net profit
    """
    opportunities = []

    for book_a, odds_a in odds_by_book_side_a.items():
        for book_b, odds_b in odds_by_book_side_b.items():
            if book_a.lower() == book_b.lower():
                continue

            result = find_arbitrage_with_fees(
                odds_a, odds_b, book_a, book_b, total_stake
            )

            if result.exists and result.net_profit_pct >= min_net_profit_pct:
                opportunities.append(result)

    # Sort by net profit descending
    opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
    return opportunities
