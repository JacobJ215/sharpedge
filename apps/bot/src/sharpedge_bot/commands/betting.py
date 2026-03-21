"""Betting commands: /bet, /result, /pending, /history."""

import logging
from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.embeds.bet_embeds import (
    bet_logged_embed,
    history_embed,
    pending_embed,
    result_embed,
)
from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_bot.services.bet_service import get_history, get_pending, log_bet, record_result
from sharpedge_db.queries.bets import get_performance_summary
from sharpedge_shared.errors import BetNotFoundError
from sharpedge_shared.types import BetResult, BetType, Sport, Tier

logger = logging.getLogger("sharpedge.commands.betting")

SPORT_CHOICES = [
    app_commands.Choice(name="NFL", value="NFL"),
    app_commands.Choice(name="NBA", value="NBA"),
    app_commands.Choice(name="MLB", value="MLB"),
    app_commands.Choice(name="NHL", value="NHL"),
    app_commands.Choice(name="NCAAF", value="NCAAF"),
    app_commands.Choice(name="NCAAB", value="NCAAB"),
    app_commands.Choice(name="Other", value="OTHER"),
]

BET_TYPE_CHOICES = [
    app_commands.Choice(name="Spread", value="SPREAD"),
    app_commands.Choice(name="Moneyline", value="MONEYLINE"),
    app_commands.Choice(name="Total (O/U)", value="TOTAL"),
    app_commands.Choice(name="Prop", value="PROP"),
    app_commands.Choice(name="Parlay", value="PARLAY"),
    app_commands.Choice(name="Teaser", value="TEASER"),
]

RESULT_CHOICES = [
    app_commands.Choice(name="Win", value="WIN"),
    app_commands.Choice(name="Loss", value="LOSS"),
    app_commands.Choice(name="Push", value="PUSH"),
]


class BettingCog(commands.Cog, name="Betting"):
    """Commands for logging and tracking bets."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="bet", description="Log a new bet")
    @app_commands.describe(
        sport="Sport",
        selection='Your pick (e.g., "Chiefs -3" or "Over 47.5")',
        odds="American odds (e.g., -110, +150)",
        units="Units wagered (e.g., 1, 1.5, 2)",
        bet_type="Type of bet",
        game="Game (e.g., Chiefs vs Raiders)",
        sportsbook="Sportsbook used",
        notes="Additional notes",
    )
    @app_commands.choices(sport=SPORT_CHOICES, bet_type=BET_TYPE_CHOICES)
    @require_tier(Tier.PRO)
    async def bet_command(
        self,
        interaction: discord.Interaction,
        sport: app_commands.Choice[str],
        selection: str,
        odds: int,
        units: float,
        bet_type: app_commands.Choice[str] | None = None,
        game: str | None = None,
        sportsbook: str | None = None,
        notes: str | None = None,
    ) -> None:
        user = interaction.extras["user"]

        bet = log_bet(
            user=user,
            sport=Sport(sport.value),
            selection=selection,
            odds=odds,
            units=Decimal(str(units)),
            bet_type=BetType(bet_type.value) if bet_type else BetType.SPREAD,
            game=game or "",
            sportsbook=sportsbook,
            notes=notes,
        )

        embed = bet_logged_embed(bet)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="result", description="Record bet result")
    @app_commands.describe(
        bet_id="Bet ID (first 8 characters from /pending)",
        result="Result: Win, Loss, or Push",
    )
    @app_commands.choices(result=RESULT_CHOICES)
    @require_tier(Tier.PRO)
    async def result_command(
        self,
        interaction: discord.Interaction,
        bet_id: str,
        result: app_commands.Choice[str],
    ) -> None:
        user = interaction.extras["user"]

        try:
            bet = record_result(user, bet_id, BetResult(result.value))
        except BetNotFoundError:
            await interaction.response.send_message(
                f"Bet `{bet_id}` not found. Use `/pending` to see your open bets.",
                ephemeral=True,
            )
            return
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        summary = get_performance_summary(user.id)
        embed = result_embed(bet, summary)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pending", description="View your pending bets")
    @require_tier(Tier.PRO)
    async def pending_command(self, interaction: discord.Interaction) -> None:
        user = interaction.extras["user"]
        bets = get_pending(user)
        embed = pending_embed(bets)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="history", description="View your bet history")
    @app_commands.describe(
        sport="Filter by sport",
        bet_type="Filter by bet type",
    )
    @app_commands.choices(sport=SPORT_CHOICES, bet_type=BET_TYPE_CHOICES)
    @require_tier(Tier.PRO)
    async def history_command(
        self,
        interaction: discord.Interaction,
        sport: app_commands.Choice[str] | None = None,
        bet_type: app_commands.Choice[str] | None = None,
    ) -> None:
        user = interaction.extras["user"]
        bets = get_history(
            user,
            sport=Sport(sport.value) if sport else None,
            bet_type=BetType(bet_type.value) if bet_type else None,
        )
        embed = history_embed(bets)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(BettingCog(bot))
