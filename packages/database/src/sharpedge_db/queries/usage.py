from datetime import datetime, timedelta, timezone

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import RateLimitResult
from sharpedge_shared.constants import RATE_LIMITS
from sharpedge_shared.types import Tier


def record_usage(user_id: str, feature: str) -> None:
    """Record a usage event for rate limiting."""
    client = get_supabase_client()
    client.table("usage").insert({
        "user_id": user_id,
        "feature": feature,
    }).execute()


def get_usage_count(user_id: str, feature: str, since: datetime) -> int:
    """Count usage events since a given time."""
    client = get_supabase_client()
    result = (
        client.table("usage")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("feature", feature)
        .gte("used_at", since.isoformat())
        .execute()
    )
    return result.count or 0


def _get_period_start(period: str) -> datetime:
    """Get the start time for a rate limit period."""
    now = datetime.now(timezone.utc)
    if period == "day":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        # Start of current week (Monday)
        days_since_monday = now.weekday()
        start = now - timedelta(days=days_since_monday)
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # "unlimited"
    return datetime.min.replace(tzinfo=timezone.utc)


def _get_period_end(period: str) -> datetime:
    """Get the reset time for a rate limit period."""
    now = datetime.now(timezone.utc)
    if period == "day":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        days_until_monday = 7 - now.weekday()
        end = now + timedelta(days=days_until_monday)
        return end.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "month":
        if now.month == 12:
            return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0)
        return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return datetime.max.replace(tzinfo=timezone.utc)


def check_rate_limit(user_id: str, feature: str, tier: Tier) -> RateLimitResult:
    """Check if a user can use a feature based on their tier's rate limits."""
    tier_limits = RATE_LIMITS.get(tier, RATE_LIMITS[Tier.FREE])
    limit_config = tier_limits.get(feature)

    if limit_config is None:
        # Feature not in rate limits = not allowed for this tier
        return RateLimitResult(allowed=False, remaining=0, reset_at=None)

    if limit_config.limit == -1:
        return RateLimitResult(allowed=True, remaining=-1, reset_at=None)

    if limit_config.limit == 0:
        return RateLimitResult(allowed=False, remaining=0, reset_at=None)

    period_start = _get_period_start(limit_config.period)
    usage_count = get_usage_count(user_id, feature, period_start)
    remaining = max(0, limit_config.limit - usage_count)
    reset_at = _get_period_end(limit_config.period)

    return RateLimitResult(
        allowed=usage_count < limit_config.limit,
        remaining=remaining,
        reset_at=reset_at,
    )
