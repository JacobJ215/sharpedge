"""Discord text formatting helpers."""

from decimal import Decimal


def format_odds(odds: int) -> str:
    """Format American odds with sign."""
    return f"+{odds}" if odds > 0 else str(odds)


def format_units(units: Decimal) -> str:
    """Format units with sign and 'u' suffix."""
    sign = "+" if units > 0 else ""
    return f"{sign}{units:.2f}u"


def format_money(amount: Decimal) -> str:
    """Format dollar amount with sign."""
    sign = "+" if amount > 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def format_percentage(pct: Decimal) -> str:
    """Format percentage with sign."""
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.2f}%"


def format_record(wins: int, losses: int, pushes: int = 0) -> str:
    """Format W-L or W-L-P record."""
    if pushes:
        return f"{wins}-{losses}-{pushes}"
    return f"{wins}-{losses}"


def result_emoji(result: str) -> str:
    """Get emoji for a bet result."""
    return {
        "WIN": "W",
        "LOSS": "L",
        "PUSH": "P",
        "PENDING": "...",
    }.get(result, "?")


def truncate(text: str, max_length: int = 1024) -> str:
    """Truncate text for Discord embed field limits."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
