"""Review commands: /review, /review-week."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.embeds.analysis_embeds import review_embed
from sharpedge_bot.middleware.rate_limiter import rate_limited
from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.commands.review")


class ReviewCog(commands.Cog, name="Review"):
    """Agent-powered review commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="review",
        description="Get a detailed review of a specific bet (AI-powered)",
    )
    @app_commands.describe(bet_id="Bet ID (first 8 characters)")
    @require_tier(Tier.PRO)
    @rate_limited("review_custom")
    async def review_command(
        self,
        interaction: discord.Interaction,
        bet_id: str,
    ) -> None:
        await interaction.response.defer()

        user = interaction.extras["user"]

        try:
            from sharpedge_bot.agents.review_agent import run_bet_review

            result_text = await run_bet_review(user.id, bet_id)
            embed = review_embed(f"BET REVIEW — #{bet_id}", result_text)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Bet review failed for bet: %s", bet_id)
            await interaction.followup.send(
                f"Review failed. Please try again.\n\nError: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="review-week",
        description="Get your weekly performance review (AI-powered)",
    )
    @require_tier(Tier.PRO)
    @rate_limited("review_weekly")
    async def review_week_command(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

        user = interaction.extras["user"]

        try:
            from sharpedge_bot.agents.review_agent import run_weekly_review

            result_text = await run_weekly_review(user.id)
            embed = review_embed("WEEKLY PERFORMANCE REVIEW", result_text)

            rate_info = interaction.extras.get("rate_limit")
            if rate_info and rate_info.remaining >= 0:
                embed.set_footer(text=f"{rate_info.remaining} weekly reviews remaining | SharpEdge")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Weekly review failed for user: %s", user.discord_id)
            await interaction.followup.send(
                f"Weekly review failed. Please try again.\n\nError: {e}",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReviewCog(bot))
