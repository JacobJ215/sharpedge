"""Core betting math: odds conversions, EV, Kelly, profit calculations."""

from decimal import Decimal

from sharpedge_db.models import KellyResult
from sharpedge_shared.types import BetResult


def american_to_decimal(odds: int) -> Decimal:
    """Convert American odds to decimal odds.

    +150 → 2.50 (win $150 on $100)
    -110 → 1.909 (win $90.91 on $100)
    """
    if odds > 0:
        return Decimal("1") + Decimal(str(odds)) / Decimal("100")
    return Decimal("1") + Decimal("100") / Decimal(str(abs(odds)))


def american_to_implied_prob(odds: int) -> Decimal:
    """Convert American odds to implied probability (0-1)."""
    if odds > 0:
        return Decimal("100") / (Decimal(str(odds)) + Decimal("100"))
    return Decimal(str(abs(odds))) / (Decimal(str(abs(odds))) + Decimal("100"))


def decimal_to_american(decimal_odds: Decimal) -> int:
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2:
        return int((decimal_odds - 1) * 100)
    return int(-100 / (decimal_odds - 1))


def calculate_potential_win(stake: Decimal, odds: int) -> Decimal:
    """Calculate potential win amount (not including stake return)."""
    decimal_odds = american_to_decimal(odds)
    return (stake * decimal_odds - stake).quantize(Decimal("0.01"))


def calculate_profit(stake: Decimal, odds: int, result: BetResult) -> Decimal:
    """Calculate actual profit/loss from a bet."""
    if result == BetResult.PUSH:
        return Decimal("0")
    if result == BetResult.LOSS:
        return -stake
    if result == BetResult.WIN:
        return calculate_potential_win(stake, odds)
    return Decimal("0")  # PENDING


def calculate_ev(true_probability: Decimal, odds: int) -> dict:
    """Calculate expected value for a bet.

    Returns dict with ev_percentage, edge, and recommendation.
    """
    implied = american_to_implied_prob(odds)
    decimal_odds = american_to_decimal(odds)
    edge = true_probability - implied

    # EV = (prob_win * win_amount) - (prob_loss * loss_amount)
    # For a $1 bet:
    ev = true_probability * (decimal_odds - 1) - (1 - true_probability)
    ev_pct = ev * 100

    return {
        "ev_percentage": ev_pct.quantize(Decimal("0.01")),
        "edge": (edge * 100).quantize(Decimal("0.01")),
        "implied_prob": (implied * 100).quantize(Decimal("0.01")),
        "true_prob": (true_probability * 100).quantize(Decimal("0.01")),
        "is_positive_ev": ev > 0,
    }


def calculate_kelly(
    odds: int,
    true_probability: Decimal,
    bankroll: Decimal | None = None,
) -> KellyResult:
    """Calculate Kelly criterion bet sizing.

    Returns full, half, and quarter Kelly as fractions of bankroll.
    """
    implied = american_to_implied_prob(odds)
    decimal_odds = american_to_decimal(odds)
    edge = true_probability - implied

    # Kelly formula: f* = (bp - q) / b
    # where b = decimal_odds - 1, p = true_prob, q = 1 - true_prob
    b = decimal_odds - 1
    p = true_probability
    q = Decimal("1") - true_probability

    full_kelly = Decimal("0") if b <= 0 else (b * p - q) / b

    # Clamp to 0 (never recommend negative sizing)
    full_kelly = max(Decimal("0"), full_kelly)

    half_kelly = (full_kelly / 2).quantize(Decimal("0.0001"))
    quarter_kelly = (full_kelly / 4).quantize(Decimal("0.0001"))

    return KellyResult(
        edge=(edge * 100).quantize(Decimal("0.01")),
        implied_prob=(implied * 100).quantize(Decimal("0.01")),
        true_prob=(true_probability * 100).quantize(Decimal("0.01")),
        full_kelly=(full_kelly * 100).quantize(Decimal("0.01")),
        half_kelly=(half_kelly * 100).quantize(Decimal("0.01")),
        quarter_kelly=(quarter_kelly * 100).quantize(Decimal("0.01")),
    )
