"""Business logic for bankroll management."""

from decimal import Decimal

from sharpedge_db.models import BankrollInfo, KellyResult, User
from sharpedge_db.queries.users import update_bankroll
from sharpedge_shared.constants import DEFAULT_UNIT_PERCENTAGE, MAX_BET_PERCENTAGE

from sharpedge_bot.utils.odds_math import calculate_kelly


def set_bankroll(discord_id: str, amount: Decimal) -> BankrollInfo:
    """Set a user's bankroll and calculate derived values."""
    user = update_bankroll(discord_id, amount)
    return _build_bankroll_info(amount)


def get_bankroll_info(user: User) -> BankrollInfo:
    """Get bankroll info for a user."""
    return _build_bankroll_info(user.bankroll)


def _build_bankroll_info(bankroll: Decimal) -> BankrollInfo:
    """Build bankroll info with unit sizing table."""
    unit_size = bankroll * Decimal(str(DEFAULT_UNIT_PERCENTAGE))
    max_bet = bankroll * Decimal(str(MAX_BET_PERCENTAGE))

    sizing_table = {
        "Low (0.5u)": f"${unit_size * Decimal('0.5'):,.2f}",
        "Medium (1.0u)": f"${unit_size:,.2f}",
        "High (1.5u)": f"${unit_size * Decimal('1.5'):,.2f}",
        "Max (3.0u)": f"${max_bet:,.2f}",
    }

    return BankrollInfo(
        bankroll=bankroll,
        unit_size=unit_size.quantize(Decimal("0.01")),
        max_bet=max_bet.quantize(Decimal("0.01")),
        sizing_table=sizing_table,
    )


def get_kelly(odds: int, probability: Decimal, bankroll: Decimal | None = None) -> KellyResult:
    """Calculate Kelly criterion sizing."""
    return calculate_kelly(odds, probability / 100, bankroll)
