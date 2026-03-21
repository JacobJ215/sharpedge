"""Betting market regime classifier for sports betting signal analysis.

Classifies the current market state into one of four regimes based on
betting percentages, line movement velocity, and book alignment.

Rule-based classifier (NOT HMM). State machine approach using priority-ordered
rules — first match wins.

# TODO: HMM upgrade path — gated on Supabase data audit confirming 700+
# observations per state per sport before switching to probabilistic model.
"""

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["REGIME_SCALE", "RegimeClassification", "RegimeState", "classify_regime"]


class RegimeState(StrEnum):
    """Four-state betting market regime classification."""

    SHARP_CONSENSUS = "SHARP_CONSENSUS"  # Sharp money aligned, handle >> tickets
    STEAM_MOVE = "STEAM_MOVE"  # Fast consensus line movement across books
    PUBLIC_HEAVY = "PUBLIC_HEAVY"  # High ticket% but low handle% (square action)
    SETTLED = "SETTLED"  # Balanced/neutral market conditions


# Alpha scale multiplier per regime (used by AlphaComposer)
REGIME_SCALE: dict[RegimeState, float] = {
    RegimeState.SHARP_CONSENSUS: 1.3,
    RegimeState.STEAM_MOVE: 1.4,
    RegimeState.PUBLIC_HEAVY: 0.8,
    RegimeState.SETTLED: 1.0,
}


@dataclass(frozen=True)
class RegimeClassification:
    """Result of market regime classification."""

    regime: RegimeState  # Classified regime state
    confidence: float  # Confidence score 0.0–1.0
    scale: float  # REGIME_SCALE value for AlphaComposer


def classify_regime(
    ticket_pct: float,  # public ticket percentage (0.0–1.0)
    handle_pct: float,  # public handle percentage (0.0–1.0)
    line_move_pts: float,  # absolute line movement since open (points)
    move_velocity: float,  # line movement speed (points per hour)
    book_alignment: float,  # fraction of books moving same direction (0.0–1.0)
) -> RegimeClassification:
    """Classify the betting market regime using rule-based priority matching.

    Rules are evaluated in priority order — first match wins:
    1. STEAM_MOVE: rapid velocity + high cross-book alignment
    2. PUBLIC_HEAVY: high ticket% but low handle% (public squares dominating)
    3. SHARP_CONSENSUS: high handle% that exceeds ticket% by significant margin
    4. SETTLED: balanced/default state

    Args:
        ticket_pct: Fraction of bets (tickets) on this side (0.0–1.0)
        handle_pct: Fraction of money (handle) on this side (0.0–1.0)
        line_move_pts: Total line movement from open in absolute points
        move_velocity: Speed of line movement in points per hour
        book_alignment: Fraction of sportsbooks moving line same direction

    Returns:
        RegimeClassification with regime state, confidence, and alpha scale
    """
    # Rule 1 (highest priority): STEAM_MOVE
    # Fast velocity + strong cross-book consensus indicates sharp steam
    if move_velocity >= 0.5 and book_alignment >= 0.75:
        confidence = min(0.9, book_alignment)
        regime = RegimeState.STEAM_MOVE

    # Rule 2: PUBLIC_HEAVY
    # Lots of tickets but low money — squares piling on, books hold firm
    elif ticket_pct >= 0.65 and handle_pct <= 0.50:
        confidence = min(0.85, ticket_pct)
        regime = RegimeState.PUBLIC_HEAVY

    # Rule 3: SHARP_CONSENSUS
    # Handle significantly exceeds tickets — sharp money dictating the market
    elif handle_pct >= 0.60 and handle_pct > ticket_pct + 0.15:
        confidence = min(0.85, handle_pct - ticket_pct + 0.5)
        regime = RegimeState.SHARP_CONSENSUS

    # Rule 4 (default): SETTLED
    # Balanced market with no strong directional signal
    else:
        confidence = 0.6
        regime = RegimeState.SETTLED

    return RegimeClassification(
        regime=regime,
        confidence=confidence,
        scale=REGIME_SCALE[regime],
    )
