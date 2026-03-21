"""Bankroll and Kelly commands: /bankroll, /kelly."""

import logging
from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.embeds.stats_embeds import bankroll_embed, kelly_embed
from sharpedge_bot.services.bankroll_service import get_bankroll_info, get_kelly, set_bankroll
from sharpedge_db.queries.users import get_or_create_user

logger = logging.getLogger("sharpedge.commands.bankroll")


class BankrollCog(commands.Cog, name="Bankroll"):
    """Bankroll management and sizing commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # --- /bankroll group ---

    bankroll_group = app_commands.Group(name="bankroll", description="Manage your bankroll")

    @bankroll_group.command(name="set", description="Set your total bankroll amount")
    @app_commands.describe(amount="Your total bankroll in dollars")
    async def bankroll_set(
        self,
        interaction: discord.Interaction,
        amount: float,
    ) -> None:
        if amount <= 0:
            await interaction.response.send_message(
                "Bankroll must be a positive number.", ephemeral=True
            )
            return

        discord_id = str(interaction.user.id)
        info = set_bankroll(discord_id, Decimal(str(amount)))
        embed = bankroll_embed(info)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @bankroll_group.command(name="view", description="View your current bankroll")
    async def bankroll_view(self, interaction: discord.Interaction) -> None:
        discord_id = str(interaction.user.id)
        user = get_or_create_user(discord_id, interaction.user.display_name)

        if user.bankroll <= 0:
            await interaction.response.send_message(
                "You haven't set a bankroll yet. Use `/bankroll set [amount]`.",
                ephemeral=True,
            )
            return

        info = get_bankroll_info(user)
        embed = bankroll_embed(info)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- /kelly ---

    @app_commands.command(name="kelly", description="Kelly Criterion bet size calculator")
    @app_commands.describe(
        odds="American odds (e.g., -110, +150)",
        probability="Your estimated true win probability (1-99)",
    )
    async def kelly_command(
        self,
        interaction: discord.Interaction,
        odds: int,
        probability: float,
    ) -> None:
        if not (1 <= probability <= 99):
            await interaction.response.send_message(
                "Probability must be between 1 and 99.", ephemeral=True
            )
            return

        if odds == 0 or odds < -10000 or odds > 10000:
            await interaction.response.send_message(
                "Enter valid American odds (e.g., -110 or +150).", ephemeral=True
            )
            return

        discord_id = str(interaction.user.id)
        user = get_or_create_user(discord_id, interaction.user.display_name)

        result = get_kelly(odds, Decimal(str(probability)))
        bankroll = user.bankroll if user.bankroll > 0 else None

        embed = kelly_embed(result, bankroll)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BankrollCog(bot))
