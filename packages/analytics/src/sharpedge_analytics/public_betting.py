"""Public betting percentage analysis.

Public betting data shows where recreational bettors are putting
their money. Sharp bettors often fade the public, especially
when ticket % diverges from money %.

Key Concepts:
- Ticket %: Percentage of individual bets on each side
- Money %: Percentage of dollars wagered on each side
- Divergence: When ticket % and money % disagree = sharp action
"""

from dataclasses import dataclass
from enum import StrEnum


class SharpIndicator(StrEnum):
    """Indicators of sharp action."""

    STRONG_SHARP = "strong_sharp"  # Clear sharp money signal
    MODERATE_SHARP = "moderate_sharp"  # Some sharp action
    NEUTRAL = "neutral"  # No clear signal
    PUBLIC_HEAVY = "public_heavy"  # Public piling on one side
    CONTRARIAN = "contrarian"  # Good fade-the-public spot


@dataclass
class PublicBettingData:
    """Public betting percentages for a game."""

    game_id: str
    game: str

    # Spread betting
    spread_ticket_home: float  # % of bets on home spread
    spread_ticket_away: float  # % of bets on away spread
    spread_money_home: float  # % of money on home spread
    spread_money_away: float  # % of money on away spread

    # Total betting
    total_ticket_over: float  # % of bets on over
    total_ticket_under: float  # % of bets on under
    total_money_over: float  # % of money on over
    total_money_under: float  # % of money on under

    # Moneyline betting
    ml_ticket_home: float  # % of bets on home ML
    ml_ticket_away: float  # % of bets on away ML
    ml_money_home: float  # % of money on home ML
    ml_money_away: float  # % of money on away ML

    source: str  # Where this data came from
    updated_at: str | None = None


@dataclass
class SharpMoneyAnalysis:
    """Analysis of sharp vs public money."""

    bet_type: str  # "spread", "total", "moneyline"
    public_side: str  # Which side public is on
    sharp_side: str | None  # Which side sharps appear to be on
    ticket_percentage: float  # % tickets on public side
    money_percentage: float  # % money on public side
    divergence: float  # Difference between money% and ticket%
    indicator: SharpIndicator
    confidence: float  # 0-1 confidence in signal
    interpretation: str


# Thresholds for sharp money detection
HEAVY_PUBLIC_THRESHOLD = 70  # 70%+ tickets = heavy public
DIVERGENCE_THRESHOLD = 10  # 10%+ difference = sharp signal
STRONG_DIVERGENCE = 15  # 15%+ difference = strong sharp signal


def analyze_sharp_money(
    data: PublicBettingData,
    bet_type: str = "spread",
) -> SharpMoneyAnalysis:
    """Analyze public vs sharp money for a bet type.

    Sharp money is detected when:
    1. Ticket % heavily favors one side (public)
    2. Money % is closer to even or opposite (sharp)
    3. Line moves toward the money side

    Args:
        data: Public betting data for the game
        bet_type: "spread", "total", or "moneyline"

    Returns:
        SharpMoneyAnalysis with interpretation
    """
    if bet_type == "spread":
        ticket_home = data.spread_ticket_home
        ticket_away = data.spread_ticket_away
        money_home = data.spread_money_home
        money_away = data.spread_money_away
        side_a, side_b = "home", "away"
    elif bet_type == "total":
        ticket_home = data.total_ticket_over
        ticket_away = data.total_ticket_under
        money_home = data.total_money_over
        money_away = data.total_money_under
        side_a, side_b = "over", "under"
    else:  # moneyline
        ticket_home = data.ml_ticket_home
        ticket_away = data.ml_ticket_away
        money_home = data.ml_money_home
        money_away = data.ml_money_away
        side_a, side_b = "home", "away"

    # Determine public side (where most tickets are)
    if ticket_home > ticket_away:
        public_side = side_a
        public_tickets = ticket_home
        public_money = money_home
        sharp_tickets = ticket_away
        sharp_money = money_away
    else:
        public_side = side_b
        public_tickets = ticket_away
        public_money = money_away
        sharp_tickets = ticket_home
        sharp_money = money_home

    # Calculate divergence
    divergence = sharp_money - sharp_tickets

    # Classify the signal
    if divergence >= STRONG_DIVERGENCE and public_tickets >= HEAVY_PUBLIC_THRESHOLD:
        indicator = SharpIndicator.STRONG_SHARP
        sharp_side = side_b if public_side == side_a else side_a
        confidence = 0.85
        interpretation = (
            f"Strong sharp money signal on {sharp_side}. "
            f"Public ({public_tickets:.0f}%) on {public_side}, "
            f"but money ({sharp_money:.0f}%) on {sharp_side}."
        )
    elif divergence >= DIVERGENCE_THRESHOLD:
        indicator = SharpIndicator.MODERATE_SHARP
        sharp_side = side_b if public_side == side_a else side_a
        confidence = 0.7
        interpretation = (
            f"Moderate sharp action detected on {sharp_side}. "
            f"Money diverging from tickets by {divergence:.0f}%."
        )
    elif public_tickets >= HEAVY_PUBLIC_THRESHOLD:
        indicator = SharpIndicator.CONTRARIAN
        sharp_side = side_b if public_side == side_a else side_a
        confidence = 0.6
        interpretation = (
            f"Contrarian spot: {public_tickets:.0f}% of public on {public_side}. "
            f"Consider fading the public on {sharp_side}."
        )
    elif public_tickets >= 60:
        indicator = SharpIndicator.PUBLIC_HEAVY
        sharp_side = None
        confidence = 0.5
        interpretation = (
            f"Public leaning {public_side} ({public_tickets:.0f}%) but "
            f"not extreme. No clear sharp signal."
        )
    else:
        indicator = SharpIndicator.NEUTRAL
        sharp_side = None
        confidence = 0.4
        interpretation = "Balanced action. No clear public or sharp lean."

    return SharpMoneyAnalysis(
        bet_type=bet_type,
        public_side=public_side,
        sharp_side=sharp_side,
        ticket_percentage=public_tickets,
        money_percentage=public_money,
        divergence=round(divergence, 1),
        indicator=indicator,
        confidence=confidence,
        interpretation=interpretation,
    )


def calculate_fade_strength(data: PublicBettingData) -> dict[str, float]:
    """Calculate strength of fade-the-public plays.

    Higher score = stronger fade opportunity.

    Args:
        data: Public betting data

    Returns:
        Dict with fade scores for each bet type
    """
    scores = {}

    for bet_type in ["spread", "total", "moneyline"]:
        analysis = analyze_sharp_money(data, bet_type)

        # Base score from ticket percentage (more lopsided = better fade)
        if analysis.ticket_percentage >= 80:
            base_score = 10
        elif analysis.ticket_percentage >= 70:
            base_score = 7
        elif analysis.ticket_percentage >= 60:
            base_score = 4
        else:
            base_score = 1

        # Bonus for divergence (sharp money)
        divergence_bonus = min(analysis.divergence / 5, 3)

        # Bonus for strong sharp indicator
        if analysis.indicator == SharpIndicator.STRONG_SHARP:
            indicator_bonus = 3
        elif analysis.indicator == SharpIndicator.MODERATE_SHARP:
            indicator_bonus = 2
        elif analysis.indicator == SharpIndicator.CONTRARIAN:
            indicator_bonus = 1
        else:
            indicator_bonus = 0

        scores[bet_type] = round(base_score + divergence_bonus + indicator_bonus, 1)

    return scores


def get_consensus_lean(data: PublicBettingData) -> dict[str, str]:
    """Get the consensus public lean for each bet type.

    Args:
        data: Public betting data

    Returns:
        Dict mapping bet type to public side
    """
    return {
        "spread": "home" if data.spread_ticket_home > data.spread_ticket_away else "away",
        "total": "over" if data.total_ticket_over > data.total_ticket_under else "under",
        "moneyline": "home" if data.ml_ticket_home > data.ml_ticket_away else "away",
    }


def format_public_betting_display(data: PublicBettingData) -> dict[str, str]:
    """Format public betting data for display.

    Args:
        data: Public betting data

    Returns:
        Dict with formatted strings for display
    """
    return {
        "spread": (
            f"Home: {data.spread_ticket_home:.0f}% tix / {data.spread_money_home:.0f}% $ | "
            f"Away: {data.spread_ticket_away:.0f}% tix / {data.spread_money_away:.0f}% $"
        ),
        "total": (
            f"Over: {data.total_ticket_over:.0f}% tix / {data.total_money_over:.0f}% $ | "
            f"Under: {data.total_ticket_under:.0f}% tix / {data.total_money_under:.0f}% $"
        ),
        "moneyline": (
            f"Home: {data.ml_ticket_home:.0f}% tix / {data.ml_money_home:.0f}% $ | "
            f"Away: {data.ml_ticket_away:.0f}% tix / {data.ml_money_away:.0f}% $"
        ),
    }


def identify_sharp_plays(
    games_data: list[PublicBettingData],
    min_divergence: float = 10,
    min_public_pct: float = 65,
) -> list[dict]:
    """Identify the best sharp money plays across multiple games.

    Args:
        games_data: List of public betting data for games
        min_divergence: Minimum money/ticket divergence
        min_public_pct: Minimum public ticket percentage

    Returns:
        List of games with sharp plays, sorted by strength
    """
    sharp_plays = []

    for data in games_data:
        for bet_type in ["spread", "total", "moneyline"]:
            analysis = analyze_sharp_money(data, bet_type)

            if (
                analysis.divergence >= min_divergence
                and analysis.ticket_percentage >= min_public_pct
                and analysis.sharp_side is not None
            ):
                sharp_plays.append(
                    {
                        "game": data.game,
                        "game_id": data.game_id,
                        "bet_type": bet_type,
                        "sharp_side": analysis.sharp_side,
                        "public_side": analysis.public_side,
                        "public_pct": analysis.ticket_percentage,
                        "divergence": analysis.divergence,
                        "indicator": analysis.indicator,
                        "confidence": analysis.confidence,
                        "interpretation": analysis.interpretation,
                    }
                )

    # Sort by confidence and divergence
    sharp_plays.sort(key=lambda x: (x["confidence"], x["divergence"]), reverse=True)

    return sharp_plays
