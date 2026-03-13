from datetime import datetime


class SharpEdgeError(Exception):
    """Base exception for all SharpEdge errors."""


class RateLimitExceeded(SharpEdgeError):
    """User has exceeded their rate limit for a feature."""

    def __init__(
        self,
        feature: str,
        remaining: int = 0,
        reset_at: datetime | None = None,
    ) -> None:
        self.feature = feature
        self.remaining = remaining
        self.reset_at = reset_at
        super().__init__(
            f"Rate limit exceeded for {feature}. "
            f"Resets at {reset_at.isoformat() if reset_at else 'unknown'}."
        )


class TierRestricted(SharpEdgeError):
    """Feature requires a higher subscription tier."""

    def __init__(self, required_tier: str, current_tier: str) -> None:
        self.required_tier = required_tier
        self.current_tier = current_tier
        super().__init__(
            f"This feature requires {required_tier} tier. "
            f"Your current tier is {current_tier}. Use /subscribe to upgrade."
        )


class InsufficientData(SharpEdgeError):
    """Not enough data to perform the requested analysis."""

    def __init__(self, message: str = "Not enough data for analysis.") -> None:
        super().__init__(message)


class ExternalAPIError(SharpEdgeError):
    """Error communicating with an external API."""

    def __init__(self, service: str, detail: str = "") -> None:
        self.service = service
        self.detail = detail
        super().__init__(f"Error from {service}: {detail}" if detail else f"Error from {service}")


class BetNotFoundError(SharpEdgeError):
    """Bet with given ID was not found."""

    def __init__(self, bet_id: str) -> None:
        self.bet_id = bet_id
        super().__init__(f"Bet #{bet_id} not found.")


class UserNotFoundError(SharpEdgeError):
    """User not found in database."""

    def __init__(self, discord_id: str) -> None:
        self.discord_id = discord_id
        super().__init__(f"User with Discord ID {discord_id} not found.")
