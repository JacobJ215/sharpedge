import functools
import logging
from collections.abc import Callable
from typing import Any

import discord

from sharpedge_bot import microcopy as tier_copy
from sharpedge_db.queries.users import get_or_create_user
from sharpedge_shared.constants import COLOR_PREMIUM
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.middleware")

# Tier hierarchy for comparison
_TIER_ORDER = {Tier.FREE: 0, Tier.PRO: 1, Tier.SHARP: 2}


def require_tier(min_tier: Tier) -> Callable:
    """Decorator that checks if a user meets the minimum tier requirement.

    Use on slash command callbacks. The user is looked up (or created) in the
    database and attached to `interaction.extras["user"]` for downstream use.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(
            self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any
        ) -> Any:
            discord_id = str(interaction.user.id)
            user = get_or_create_user(discord_id, interaction.user.display_name)

            # Attach user to interaction for downstream access
            if not hasattr(interaction, "extras"):
                interaction.extras = {}
            interaction.extras["user"] = user

            user_tier_level = _TIER_ORDER.get(user.tier, 0)
            required_level = _TIER_ORDER.get(min_tier, 0)

            if user_tier_level < required_level:
                embed = discord.Embed(
                    title=tier_copy.tier_gate_title(min_tier),
                    description=tier_copy.tier_gate_description(min_tier, user.tier),
                    color=COLOR_PREMIUM,
                )
                embed.set_footer(text=tier_copy.tier_gate_footer(min_tier))
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator
