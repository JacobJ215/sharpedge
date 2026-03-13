"""Business logic for performance stats and analytics."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sharpedge_db.models import (
    BetTypeBreakdown,
    CLVSummary,
    PerformanceSummary,
    SportBreakdown,
    User,
)
from sharpedge_db.queries.bets import (
    get_breakdown_by_bet_type,
    get_breakdown_by_sport,
    get_clv_summary,
    get_performance_summary,
)


def _resolve_dates(period: str) -> tuple[date | None, date | None]:
    """Resolve a period string to start/end dates."""
    today = datetime.now(timezone.utc).date()
    if period == "today":
        return today, today
    if period == "week":
        return today - timedelta(days=7), today
    if period == "month":
        return today - timedelta(days=30), today
    if period == "season":
        year = today.year if today.month >= 9 else today.year - 1
        return date(year, 9, 1), today
    return None, None  # all time


def get_full_stats(
    user: User,
    period: str = "all",
) -> dict:
    """Get comprehensive stats for a user."""
    start, end = _resolve_dates(period)

    summary = get_performance_summary(user.id, start, end)
    by_sport = get_breakdown_by_sport(user.id, start, end)
    by_type = get_breakdown_by_bet_type(user.id, start, end)
    clv = get_clv_summary(user.id, start, end)

    return {
        "summary": summary,
        "by_sport": by_sport,
        "by_type": by_type,
        "clv": clv,
        "period": period,
    }


def get_sport_stats(user: User, sport: str, period: str = "all") -> dict:
    """Get stats filtered to a single sport."""
    start, end = _resolve_dates(period)
    summary = get_performance_summary(user.id, start, end)
    return {"summary": summary, "sport": sport, "period": period}
