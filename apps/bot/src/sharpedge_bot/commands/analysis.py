"""Analysis commands: /analyze, /value, /movement."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_shared.types import Sport, Tier

from sharpedge_bot.commands.betting import SPORT_CHOICES
from sharpedge_bot.embeds.analysis_embeds import analysis_embed
from sharpedge_bot.middleware.rate_limiter import rate_limited
from sharpedge_bot.middleware.tier_check import require_tier

logger = logging.getLogger("sharpedge.commands.analysis")


class AnalysisCog(commands.Cog, name="Analysis"):
    """Agent-powered analysis commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="analyze",
        description="Get comprehensive game analysis (AI-powered)",
    )
    @app_commands.describe(
        game='Game to analyze (e.g., "Chiefs Raiders" or "KC vs LV")',
        sport="Sport (auto-detected if not specified)",
    )
    @app_commands.choices(sport=SPORT_CHOICES)
    @rate_limited("analysis")
    async def analyze_command(
        self,
        interaction: discord.Interaction,
        game: str,
        sport: app_commands.Choice[str] | None = None,
    ) -> None:
        # Defer since agent may take several seconds
        await interaction.response.defer()

        try:
            from sharpedge_bot.agents.game_analyst import run_game_analysis

            sport_val = sport.value if sport else ""
            result_text = await run_game_analysis(game, sport_val)

            embed = analysis_embed(game, result_text)

            # Add rate limit info in footer
            rate_info = interaction.extras.get("rate_limit")
            if rate_info and rate_info.remaining >= 0:
                embed.set_footer(
                    text=f"{rate_info.remaining} analyses remaining today | SharpEdge"
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Analysis failed for game: %s", game)
            await interaction.followup.send(
                f"Analysis failed. Please try again later.\n\nError: {e}",
                ephemeral=True,
            )

    @app_commands.command(
        name="value",
        description="Find today's value plays across all games",
    )
    @app_commands.describe(sport="Filter by sport")
    @app_commands.choices(sport=SPORT_CHOICES)
    @require_tier(Tier.PRO)
    @rate_limited("analysis")
    async def value_command(
        self,
        interaction: discord.Interaction,
        sport: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer()

        try:
            from sharpedge_bot.agents.game_analyst import run_game_analysis

            sport_val = sport.value if sport else "all major sports"
            prompt = f"Find today's best value plays for {sport_val}"
            result_text = await run_game_analysis(prompt, sport_val)

            embed = discord.Embed(
                title=f"TODAY'S VALUE PLAYS — {sport_val.upper() if sport else 'ALL SPORTS'}",
                color=0x00FF00,
            )

            # Split into fields
            chunks = result_text[:4000]  # Discord embed limit
            embed.description = chunks
            embed.set_footer(text="SharpEdge | Not financial advice")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Value finder failed")
            await interaction.followup.send(
                f"Could not find value plays. Please try again.\n\nError: {e}",
                ephemeral=True,
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AnalysisCog(bot))
