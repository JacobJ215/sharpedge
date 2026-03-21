import functools
import logging
from collections.abc import Callable
from typing import Any

import discord

from sharpedge_db.queries.usage import check_rate_limit, record_usage
from sharpedge_db.queries.users import get_or_create_user
from sharpedge_shared.constants import COLOR_WARNING
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.middleware")


def rate_limited(feature: str) -> Callable:
    """Decorator that enforces rate limits for a feature.

    Checks the user's tier, looks up their usage, and blocks if limit exceeded.
    Records usage on success. Attaches rate limit info to interaction.extras.

    Should be applied AFTER @require_tier if both are used, so the user
    object is already on interaction.extras.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
            self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> Any:
            discord_id = str(interaction.user.id)

            # Get user (may already be on interaction from tier_check)
            extras = getattr(interaction, "extras", {})
            user = extras.get("user")
            if user is None:
                user = get_or_create_user(discord_id, interaction.user.display_name)
                if not hasattr(interaction, "extras"):
                    interaction.extras = {}
                interaction.extras["user"] = user

            # Check rate limit
            result = check_rate_limit(user.id, feature, Tier(user.tier))

            if not result.allowed:
                embed = discord.Embed(
                    title="Rate Limit Reached",
                    description=_format_limit_message(feature, user.tier, result.reset_at),
                    color=COLOR_WARNING,
                )
                if user.tier == Tier.FREE:
                    embed.add_field(
                        name="Want more?",
                        value="Upgrade to Pro for unlimited access. Use `/subscribe`.",
                        inline=False,
                    )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None

            # Record this usage
            record_usage(user.id, feature)

            # Attach remaining info for the command to use in footer
            interaction.extras["rate_limit"] = result

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator


def _format_limit_message(feature: str, tier: str, reset_at: Any) -> str:
    """Format a user-friendly rate limit message."""
    feature_names = {
        "analysis": "game analyses",
        "alerts_value": "value alerts",
        "alerts_movement": "line movement alerts",
        "review_weekly": "weekly reviews",
        "review_monthly": "monthly reviews",
        "review_custom": "custom analyses",
    }
    name = feature_names.get(feature, feature)

    msg = f"You've used all your {name} for this period."
    if reset_at:
        msg += f"\n\nResets: <t:{int(reset_at.timestamp())}:R>"
    return msg
