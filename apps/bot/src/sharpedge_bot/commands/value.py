"""Value play commands - show +EV opportunities."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.middleware.rate_limiter import rate_limited
from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.commands.value")


class ValueCog(commands.Cog):
    """Commands for finding value betting opportunities."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="value", description="Show current +EV betting opportunities")
    @app_commands.describe(
        sport="Filter by sport",
        min_ev="Minimum EV percentage (default: 2.0)",
    )
    @app_commands.choices(
        sport=[
            app_commands.Choice(name="All Sports", value="all"),
            app_commands.Choice(name="NFL", value="NFL"),
            app_commands.Choice(name="NBA", value="NBA"),
            app_commands.Choice(name="MLB", value="MLB"),
            app_commands.Choice(name="NHL", value="NHL"),
        ]
    )
    @require_tier(Tier.PRO)
    @rate_limited("value_scan")
    async def value_command(
        self,
        interaction: discord.Interaction,
        sport: str = "all",
        min_ev: float = 2.0,
    ):
        """Show active positive EV betting opportunities."""
        await interaction.response.defer()

        from sharpedge_db.queries.value_plays import get_active_value_plays

        sport_filter = None if sport == "all" else sport
        plays = get_active_value_plays(sport=sport_filter, min_ev=min_ev, limit=10)

        if not plays:
            embed = discord.Embed(
                title="Value Scanner",
                description="No value plays currently detected above your threshold.",
                color=0x808080,
            )
            embed.add_field(
                name="Tips",
                value=(
                    "• Lower the min EV threshold\n"
                    "• Check back in a few minutes\n"
                    "• Value plays appear when model projections differ from market"
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="💰 Active Value Plays",
            description=f"Found **{len(plays)}** opportunities with EV ≥ {min_ev}%",
            color=0x00FF00,
        )

        for i, play in enumerate(plays[:5], 1):
            confidence_emoji = {
                "HIGH": "🟢",
                "MEDIUM": "🟡",
                "LOW": "🟠",
            }.get(play.get("confidence", "LOW"), "⚪")

            odds = play.get("market_odds", 0)
            odds_str = f"+{odds}" if odds > 0 else str(odds)

            embed.add_field(
                name=f"{i}. {play.get('game', 'Unknown')}",
                value=(
                    f"**{play.get('side', '')}** @ {play.get('sportsbook', '')}\n"
                    f"Odds: {odds_str} | EV: **+{play.get('ev_percentage', 0):.1f}%** | "
                    f"Edge: {play.get('edge_percentage', 0):.1f}%\n"
                    f"{confidence_emoji} {play.get('confidence', 'LOW')} confidence"
                ),
                inline=False,
            )

        if len(plays) > 5:
            embed.set_footer(text=f"Showing top 5 of {len(plays)} plays")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="arb", description="Show arbitrage opportunities")
    @app_commands.describe(min_profit="Minimum profit percentage (default: 0.5)")
    @require_tier(Tier.SHARP)
    @rate_limited("arb_scan")
    async def arb_command(
        self,
        interaction: discord.Interaction,
        min_profit: float = 0.5,
    ):
        """Show active arbitrage opportunities."""
        await interaction.response.defer()

        from sharpedge_db.queries.arbitrage import get_active_arbitrage

        arbs = get_active_arbitrage(min_profit=min_profit)

        if not arbs:
            embed = discord.Embed(
                title="Arbitrage Scanner",
                description="No arbitrage opportunities currently available.",
                color=0x808080,
            )
            embed.add_field(
                name="About Arbs",
                value=(
                    "Arbitrage opportunities are rare and disappear quickly.\n"
                    "They occur when sportsbooks disagree enough that you can\n"
                    "bet both sides for guaranteed profit."
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="⚡ Arbitrage Opportunities",
            description=f"Found **{len(arbs)}** guaranteed profit opportunities",
            color=0x00FF00,
        )

        for i, arb in enumerate(arbs[:3], 1):
            odds_a = arb.get("odds_a", 0)
            odds_b = arb.get("odds_b", 0)
            odds_a_str = f"+{odds_a}" if odds_a > 0 else str(odds_a)
            odds_b_str = f"+{odds_b}" if odds_b > 0 else str(odds_b)

            # Calculate example stakes for $1000
            stake_a = arb.get("stake_a_percentage", 50) * 10
            stake_b = arb.get("stake_b_percentage", 50) * 10
            profit = arb.get("profit_percentage", 0) * 10

            embed.add_field(
                name=f"{i}. {arb.get('game', 'Unknown')} ({arb.get('bet_type', '')})",
                value=(
                    f"**{arb.get('book_a', '')}**: {arb.get('side_a', '')} @ {odds_a_str}\n"
                    f"**{arb.get('book_b', '')}**: {arb.get('side_b', '')} @ {odds_b_str}\n"
                    f"📊 Profit: **{arb.get('profit_percentage', 0):.2f}%**\n"
                    f"💵 $1000 split: ${stake_a:.0f} / ${stake_b:.0f} = **${profit:.2f} profit**"
                ),
                inline=False,
            )

        embed.set_footer(text="⚠️ Act fast - arbs disappear within minutes!")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="sharp", description="Show sharp money indicators")
    @app_commands.describe(sport="Filter by sport")
    @app_commands.choices(
        sport=[
            app_commands.Choice(name="All Sports", value="all"),
            app_commands.Choice(name="NFL", value="NFL"),
            app_commands.Choice(name="NBA", value="NBA"),
            app_commands.Choice(name="MLB", value="MLB"),
            app_commands.Choice(name="NHL", value="NHL"),
        ]
    )
    @require_tier(Tier.PRO)
    @rate_limited("sharp_scan")
    async def sharp_command(
        self,
        interaction: discord.Interaction,
        sport: str = "all",
    ):
        """Show games with sharp money indicators."""
        await interaction.response.defer()

        from sharpedge_db.queries.public_betting import get_sharp_plays

        sport_filter = None if sport == "all" else sport
        plays = get_sharp_plays(min_divergence=10, sport=sport_filter)

        if not plays:
            embed = discord.Embed(
                title="Sharp Money Scanner",
                description="No strong sharp money signals detected.",
                color=0x808080,
            )
            embed.add_field(
                name="What is Sharp Money?",
                value=(
                    "Sharp money is identified when:\n"
                    "• Money % diverges from ticket %\n"
                    "• Professional bettors bet larger amounts\n"
                    "• Line moves opposite to public betting"
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🎯 Sharp Money Indicators",
            description=f"Found **{len(plays)}** games with sharp action",
            color=0x9932CC,
        )

        for i, play in enumerate(plays[:5], 1):
            divergence = play.get("divergence", 0)
            signal = "🔥 STRONG" if divergence >= 15 else "📊 MODERATE"

            embed.add_field(
                name=f"{i}. {play.get('home_team', '')} vs {play.get('away_team', '')}",
                value=(
                    f"**Public**: {play.get('public_pct', 0):.0f}% on {play.get('public_side', '')}\n"
                    f"**Sharp**: Money on **{play.get('sharp_side', '').upper()}**\n"
                    f"Divergence: {divergence:.1f}% | {signal}"
                ),
                inline=False,
            )

        embed.set_footer(text="Sharp money = where professional bettors are betting")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(ValueCog(bot))
