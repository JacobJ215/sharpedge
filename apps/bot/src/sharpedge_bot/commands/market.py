"""Market analysis commands - consensus, movements, key numbers."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.commands.market")


class MarketCog(commands.Cog):
    """Commands for market analysis and line information."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="consensus", description="Get market consensus line for a game")
    @app_commands.describe(game="Game to look up (e.g., 'Chiefs Raiders')")
    @require_tier(Tier.PRO)
    async def consensus_command(
        self,
        interaction: discord.Interaction,
        game: str,
    ):
        """Show market consensus for a game."""
        await interaction.response.defer()

        from sharpedge_bot.services.odds_service import get_odds_client
        from sharpedge_db.queries.consensus import get_consensus
        from sharpedge_db.queries.opening_lines import get_opening_line

        # Find the game
        odds_client = get_odds_client()
        game_data = await odds_client.find_game(game)

        if not game_data:
            await interaction.followup.send(f"Could not find game: {game}")
            return

        game_id = game_data.id
        home_team = game_data.home_team
        away_team = game_data.away_team

        consensus = get_consensus(game_id)
        opening = get_opening_line(game_id, "spread")

        embed = discord.Embed(
            title="📊 Market Consensus",
            description=f"**{away_team} @ {home_team}**",
            color=0x3498DB,
        )

        if consensus:
            # Spread consensus
            spread_line = consensus.get("spread_consensus", 0)
            spread_weighted = consensus.get("spread_weighted_consensus", spread_line)
            spread_min = consensus.get("spread_min", 0)
            spread_max = consensus.get("spread_max", 0)
            spread_books = consensus.get("spread_books_count", 0)

            spread_fair_home = consensus.get("spread_fair_home_prob", 0.5)
            spread_fair_away = consensus.get("spread_fair_away_prob", 0.5)

            embed.add_field(
                name="Spread Consensus",
                value=(
                    f"**{home_team} {spread_line:+.1f}**\n"
                    f"Weighted: {spread_weighted:+.1f}\n"
                    f"Range: {spread_min:+.1f} to {spread_max:+.1f}\n"
                    f"({spread_books} books)"
                ),
                inline=True,
            )

            embed.add_field(
                name="Fair Probabilities",
                value=(
                    f"{home_team}: {spread_fair_home * 100:.1f}%\n"
                    f"{away_team}: {spread_fair_away * 100:.1f}%"
                ),
                inline=True,
            )

            # Total consensus
            total_line = consensus.get("total_consensus", 0)
            total_min = consensus.get("total_min", 0)
            total_max = consensus.get("total_max", 0)

            total_fair_over = consensus.get("total_fair_over_prob", 0.5)
            total_fair_under = consensus.get("total_fair_under_prob", 0.5)

            embed.add_field(
                name="Total Consensus",
                value=(
                    f"**{total_line:.1f}**\n"
                    f"Range: {total_min:.1f} to {total_max:.1f}\n"
                    f"Over: {total_fair_over * 100:.1f}% | Under: {total_fair_under * 100:.1f}%"
                ),
                inline=False,
            )

            # Market agreement
            agreement = consensus.get("market_agreement", 100)
            if agreement < 50:
                agreement_text = f"⚠️ Low ({agreement:.0f}%) - books disagree"
            elif agreement < 80:
                agreement_text = f"📊 Moderate ({agreement:.0f}%)"
            else:
                agreement_text = f"✅ High ({agreement:.0f}%)"

            embed.add_field(
                name="Market Agreement",
                value=agreement_text,
                inline=True,
            )

        if opening:
            opening_line = opening.get("line", 0)
            movement = (consensus.get("spread_consensus", 0) if consensus else 0) - opening_line

            if abs(movement) >= 0.5:
                direction = "toward favorite" if movement < 0 else "toward underdog"
                embed.add_field(
                    name="Movement from Open",
                    value=f"Opened: {opening_line:+.1f}\nMoved {abs(movement):.1f} pts {direction}",
                    inline=True,
                )

        if not consensus and not opening:
            embed.add_field(
                name="Data Not Available",
                value="Consensus data not yet calculated for this game.",
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="steam", description="Show recent steam moves (sharp line movements)"
    )
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
    async def steam_command(
        self,
        interaction: discord.Interaction,
        sport: str = "all",
    ):
        """Show recent steam moves."""
        await interaction.response.defer()

        from sharpedge_db.queries.line_movements import get_recent_steam_moves

        sport_filter = None if sport == "all" else sport
        moves = get_recent_steam_moves(hours=24, sport=sport_filter)

        if not moves:
            embed = discord.Embed(
                title="Steam Move Scanner",
                description="No steam moves detected in the last 24 hours.",
                color=0x808080,
            )
            embed.add_field(
                name="What is a Steam Move?",
                value=(
                    "A steam move is a sharp, sudden line movement\n"
                    "across multiple sportsbooks, indicating coordinated\n"
                    "betting from professional bettors."
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🚂 Recent Steam Moves",
            description=f"Found **{len(moves)}** steam moves in the last 24 hours",
            color=0xFF4500,
        )

        for i, move in enumerate(moves[:5], 1):
            old_line = move.get("old_line", 0)
            new_line = move.get("new_line", 0)
            magnitude = abs(new_line - old_line)
            direction = "⬆️" if new_line > old_line else "⬇️"

            embed.add_field(
                name=f"{i}. {move.get('sport', '')} - {move.get('bet_type', '')}",
                value=(
                    f"Game: {move.get('game_id', '')[:20]}\n"
                    f"{direction} {old_line:.1f} → **{new_line:.1f}** ({magnitude:.1f} pts)\n"
                    f"Interpretation: {move.get('interpretation', 'Sharp action detected')}"
                ),
                inline=False,
            )

        embed.set_footer(text="Steam moves often indicate where sharp money is going")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="fade", description="Show games where public is heavily on one side")
    @app_commands.describe(
        sport="Filter by sport",
        min_public="Minimum public percentage (default: 70)",
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
    async def fade_command(
        self,
        interaction: discord.Interaction,
        sport: str = "all",
        min_public: float = 70,
    ):
        """Show contrarian fade opportunities."""
        await interaction.response.defer()

        from sharpedge_db.queries.public_betting import get_contrarian_plays

        sport_filter = None if sport == "all" else sport
        plays = get_contrarian_plays(min_public_pct=min_public, sport=sport_filter)

        if not plays:
            embed = discord.Embed(
                title="Fade the Public Scanner",
                description=f"No games with {min_public}%+ public on one side.",
                color=0x808080,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="🔄 Fade the Public",
            description="Games where public is heavily lopsided",
            color=0x9932CC,
        )

        for _i, play in enumerate(plays[:6], 1):
            emoji = (
                "🏈"
                if play.get("sport") == "NFL"
                else "🏀"
                if play.get("sport") == "NBA"
                else "⚾"
                if play.get("sport") == "MLB"
                else "🏒"
            )

            embed.add_field(
                name=f"{emoji} {play.get('game_id', '')[:25]}...",
                value=(
                    f"**{play.get('public_pct', 0):.0f}%** on {play.get('public_side', '')}\n"
                    f"Fade: **{play.get('fade_side', '').upper()}**\n"
                    f"Type: {play.get('bet_type', '')}"
                ),
                inline=True,
            )

        embed.set_footer(text="Historical data shows fading heavy public sides can be profitable")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(MarketCog(bot))
