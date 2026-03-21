from dataclasses import dataclass

from sharpedge_shared.types import Tier


@dataclass(frozen=True)
class RateLimit:
    limit: int  # -1 = unlimited
    period: str  # "day", "week", "month"


# Rate limits per tier per feature
RATE_LIMITS: dict[Tier, dict[str, RateLimit]] = {
    Tier.FREE: {
        "analysis": RateLimit(limit=3, period="day"),
        "alerts_value": RateLimit(limit=0, period="day"),
        "alerts_movement": RateLimit(limit=0, period="day"),
        "review_weekly": RateLimit(limit=0, period="week"),
        "review_monthly": RateLimit(limit=0, period="month"),
        "review_custom": RateLimit(limit=0, period="month"),
        "value_scan": RateLimit(limit=0, period="day"),
        "arb_scan": RateLimit(limit=0, period="day"),
        "sharp_scan": RateLimit(limit=0, period="day"),
    },
    Tier.PRO: {
        "analysis": RateLimit(limit=-1, period="day"),
        "alerts_value": RateLimit(limit=5, period="day"),
        "alerts_movement": RateLimit(limit=10, period="day"),
        "review_weekly": RateLimit(limit=1, period="week"),
        "review_monthly": RateLimit(limit=1, period="month"),
        "review_custom": RateLimit(limit=2, period="month"),
        "value_scan": RateLimit(limit=20, period="day"),
        "arb_scan": RateLimit(limit=0, period="day"),  # Arbs are Sharp only
        "sharp_scan": RateLimit(limit=20, period="day"),
    },
    Tier.SHARP: {
        "analysis": RateLimit(limit=-1, period="day"),
        "alerts_value": RateLimit(limit=-1, period="day"),
        "alerts_movement": RateLimit(limit=-1, period="day"),
        "review_weekly": RateLimit(limit=3, period="week"),
        "review_monthly": RateLimit(limit=2, period="month"),
        "review_custom": RateLimit(limit=5, period="month"),
        "value_scan": RateLimit(limit=-1, period="day"),
        "arb_scan": RateLimit(limit=-1, period="day"),
        "sharp_scan": RateLimit(limit=-1, period="day"),
    },
}

# Display / legacy Stripe-style prices in cents (Whop is source of truth at checkout)
TIER_PRICES: dict[Tier, int] = {
    Tier.PRO: 1999,  # $19.99/month
    Tier.SHARP: 4999,  # $49.99/month
}

# Minimum EV percentage to trigger a value alert
EV_THRESHOLD: float = 1.5

# Minimum line movement (points) to trigger a movement alert
LINE_MOVEMENT_THRESHOLD: float = 0.5

# Bankroll management defaults
DEFAULT_UNIT_PERCENTAGE: float = 0.01  # 1% of bankroll
MAX_BET_PERCENTAGE: float = 0.03  # 3% of bankroll

# Discord embed colors
COLOR_SUCCESS = 0x00FF00  # Green
COLOR_ERROR = 0xFF0000  # Red
COLOR_WARNING = 0xFFA500  # Orange
COLOR_INFO = 0x3498DB  # Blue
COLOR_PREMIUM = 0xFFD700  # Gold
COLOR_ALERT = 0xFF4444  # Bright red

# Bot presence
BOT_STATUS = "Analyzing games... | /help"
