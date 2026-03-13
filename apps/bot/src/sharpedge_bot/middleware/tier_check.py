import functools
import logging
from collections.abc import Callable
from typing import Any

import discord

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
        async def wrapper(self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any) -> Any:
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
                    title="Pro Feature",
                    description=(
                        f"This feature requires **{min_tier.value.title()}** tier.\n"
                        f"Your current tier: **{user.tier.value.title()}**\n\n"
                        "Use `/subscribe` to upgrade and unlock:\n"
                        "- Unlimited game analysis\n"
                        "- Bet logging & performance tracking\n"
                        "- Value alerts & line movement alerts\n"
                        "- Weekly performance reviews"
                    ),
                    color=COLOR_PREMIUM,
                )
                embed.set_footer(text="SharpEdge Pro — $49/month")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return None

            return await func(self, interaction, *args, **kwargs)

        return wrapper

    return decorator
