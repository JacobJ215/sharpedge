"""Business logic for bet logging and result tracking."""

import logging
from datetime import date
from decimal import Decimal

from sharpedge_db.models import Bet, User
from sharpedge_db.queries.bets import (
    create_bet,
    get_bet_by_id,
    get_bet_history,
    get_pending_bets,
    update_bet_result,
)
from sharpedge_shared.errors import BetNotFoundError
from sharpedge_shared.types import BetResult, BetType, Sport

from sharpedge_bot.utils.odds_math import calculate_potential_win, calculate_profit

logger = logging.getLogger("sharpedge.services.bet")


def log_bet(
    user: User,
    sport: Sport,
    selection: str,
    odds: int,
    units: Decimal,
    bet_type: BetType = BetType.SPREAD,
    game: str = "",
    sportsbook: str | None = None,
    notes: str | None = None,
    game_date: date | None = None,
) -> Bet:
    """Log a new bet for a user."""
    # Calculate stake from units and user's unit size
    if user.unit_size > 0:
        stake = units * user.unit_size
    else:
        # Default to $50 unit if bankroll not set
        stake = units * Decimal("50")

    potential_win = calculate_potential_win(stake, odds)

    # Auto-detect game name from selection if not provided
    if not game:
        game = selection.split()[0] if selection else "Unknown"

    bet = create_bet(
        user_id=user.id,
        sport=sport,
        game=game,
        bet_type=bet_type,
        selection=selection,
        odds=odds,
        units=units,
        stake=stake,
        potential_win=potential_win,
        sportsbook=sportsbook,
        notes=notes,
        game_date=game_date,
    )

    logger.info(
        "Bet logged: %s | %s | %s | %s %du @ %s",
        user.discord_id, sport, selection, f"{odds:+}", units, sportsbook or "N/A",
    )
    return bet


def record_result(user: User, bet_id: str, result: BetResult) -> Bet:
    """Record the result of an existing bet."""
    bet = get_bet_by_id(bet_id)
    if bet is None:
        raise BetNotFoundError(bet_id)

    if bet.user_id != user.id:
        raise BetNotFoundError(bet_id)

    if bet.result != BetResult.PENDING:
        raise ValueError(f"Bet #{bet_id} already settled as {bet.result}.")

    profit = calculate_profit(bet.stake, bet.odds, result)

    updated = update_bet_result(
        bet_id=bet_id,
        result=result,
        profit=profit,
    )

    emoji = {"WIN": "W", "LOSS": "L", "PUSH": "P"}.get(result, "?")
    logger.info(
        "Result recorded: %s | Bet #%s | %s | %s",
        user.discord_id, bet_id[:8], emoji, f"${profit:+.2f}",
    )
    return updated


def get_pending(user: User) -> list[Bet]:
    """Get all pending bets for a user."""
    return get_pending_bets(user.id)


def get_history(
    user: User,
    limit: int = 20,
    sport: Sport | None = None,
    bet_type: BetType | None = None,
) -> list[Bet]:
    """Get bet history for a user."""
    return get_bet_history(
        user_id=user.id,
        limit=limit,
        sport=sport,
        bet_type=bet_type,
    )
