"""Stats command: /stats."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_shared.types import Tier

from sharpedge_bot.embeds.stats_embeds import stats_overview_embed
from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_bot.services.stats_service import get_full_stats

logger = logging.getLogger("sharpedge.commands.stats")

PERIOD_CHOICES = [
    app_commands.Choice(name="All Time", value="all"),
    app_commands.Choice(name="Today", value="today"),
    app_commands.Choice(name="This Week", value="week"),
    app_commands.Choice(name="This Month", value="month"),
    app_commands.Choice(name="This Season", value="season"),
]


class StatsCog(commands.Cog, name="Stats"):
    """Performance tracking commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="stats", description="View your performance stats")
    @app_commands.describe(period="Time period to analyze")
    @app_commands.choices(period=PERIOD_CHOICES)
    @require_tier(Tier.PRO)
    async def stats_command(
        self,
        interaction: discord.Interaction,
        period: app_commands.Choice[str] | None = None,
    ) -> None:
        user = interaction.extras["user"]
        period_val = period.value if period else "all"

        data = get_full_stats(user, period_val)

        embed = stats_overview_embed(
            summary=data["summary"],
            by_sport=data["by_sport"],
            by_type=data["by_type"],
            clv=data["clv"],
            period=period_val,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StatsCog(bot))
