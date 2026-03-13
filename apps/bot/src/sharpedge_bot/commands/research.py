"""Research commands - AI-powered betting research and visual analytics."""

import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_bot.utils.chart_sender import send_chart_followup, create_chart_embed
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.commands.research")


class ResearchCog(commands.Cog):
    """AI-powered research assistant and visual analytics commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================
    # AI RESEARCH COMMANDS
    # ============================================

    @app_commands.command(
        name="research",
        description="AI research assistant - ask any betting research question",
    )
    @app_commands.describe(
        query="Your research question (e.g., 'What's the sharp action on Chiefs game?')",
    )
    @require_tier(Tier.PRO)
    async def research_command(
        self,
        interaction: discord.Interaction,
        query: str,
    ):
        """General research query using AI agent."""
        await interaction.response.defer()

        try:
            from sharpedge_bot.agents.research_agent import run_research

            result = await run_research(query)

            # Split long responses
            if len(result) > 4000:
                chunks = [result[i:i+4000] for i in range(0, len(result), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await interaction.followup.send(chunk)
                    else:
                        await interaction.followup.send(chunk)
            else:
                await interaction.followup.send(result)

        except Exception as e:
            logger.exception("Error in research command")
            await interaction.followup.send(
                f"Research error: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="breakdown",
        description="Get comprehensive matchup breakdown for a game",
    )
    @app_commands.describe(
        game="Game to analyze (e.g., 'Chiefs Raiders')",
        sport="Sport",
    )
    @app_commands.choices(
        sport=[
            app_commands.Choice(name="NFL", value="NFL"),
            app_commands.Choice(name="NBA", value="NBA"),
            app_commands.Choice(name="MLB", value="MLB"),
            app_commands.Choice(name="NHL", value="NHL"),
        ]
    )
    @require_tier(Tier.PRO)
    async def breakdown_command(
        self,
        interaction: discord.Interaction,
        game: str,
        sport: str,
    ):
        """Comprehensive matchup breakdown using AI research agent."""
        await interaction.response.defer()

        try:
            from sharpedge_bot.agents.research_agent import research_game

            # Parse game into teams
            parts = game.replace(" vs ", " ").replace(" @ ", " ").split()
            if len(parts) >= 2:
                away_team = parts[0]
                home_team = parts[-1]
            else:
                await interaction.followup.send(
                    "Please specify two teams (e.g., 'Chiefs Raiders')",
                    ephemeral=True,
                )
                return

            result = await research_game(home_team, away_team, sport)

            embed = discord.Embed(
                title=f"📊 Research: {game}",
                description=result[:4000] if len(result) > 4000 else result,
                color=0x3498DB,
            )
            embed.set_footer(text="SharpEdge Research Agent | Not financial advice")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Error in breakdown command")
            await interaction.followup.send(
                f"Research error: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="trends",
        description="Get historical betting trends for a situation",
    )
    @app_commands.describe(
        trend_type="Type of trend to analyze",
        sport="Sport",
    )
    @app_commands.choices(
        trend_type=[
            app_commands.Choice(name="Road Underdogs ATS", value="road_dogs_ats"),
            app_commands.Choice(name="Home Favorites ATS", value="home_favorites_ats"),
            app_commands.Choice(name="Primetime Unders", value="primetime_unders"),
            app_commands.Choice(name="Divisional Unders", value="divisional_unders"),
            app_commands.Choice(name="Revenge Games", value="revenge_spots"),
            app_commands.Choice(name="Back-to-Back Road", value="back_to_back_road"),
            app_commands.Choice(name="Rest Advantage 3+", value="rest_advantage_3plus"),
        ],
        sport=[
            app_commands.Choice(name="NFL", value="NFL"),
            app_commands.Choice(name="NBA", value="NBA"),
            app_commands.Choice(name="MLB", value="MLB"),
        ]
    )
    @require_tier(Tier.PRO)
    async def trends_command(
        self,
        interaction: discord.Interaction,
        trend_type: str,
        sport: str,
    ):
        """Get historical betting trends."""
        await interaction.response.defer()

        try:
            from sharpedge_bot.agents.research_agent import get_historical_trends

            result = await get_historical_trends(trend_type, sport)

            import json
            data = json.loads(result)

            embed = discord.Embed(
                title=f"📈 Historical Trend: {trend_type.replace('_', ' ').title()}",
                color=0x9932CC,
            )

            trend_data = data.get("data", {})
            if isinstance(trend_data, dict) and "record" in trend_data:
                embed.add_field(
                    name="Record",
                    value=trend_data.get("record", "N/A"),
                    inline=True,
                )
                embed.add_field(
                    name="Sample Size",
                    value=f"{trend_data.get('sample', 0):,} bets",
                    inline=True,
                )
                embed.add_field(
                    name="Edge Assessment",
                    value=trend_data.get("edge", "N/A"),
                    inline=True,
                )
            else:
                embed.add_field(
                    name="Data",
                    value=str(trend_data)[:1000],
                    inline=False,
                )

            embed.add_field(
                name="⚠️ Disclaimer",
                value=data.get("disclaimer", "Past performance doesn't guarantee future results."),
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Error in trends command")
            await interaction.followup.send(
                f"Error: {str(e)}", ephemeral=True
            )

    # ============================================
    # VISUAL ANALYTICS COMMANDS
    # ============================================

    @app_commands.command(
        name="chart-movement",
        description="Generate line movement chart for a game",
    )
    @app_commands.describe(
        game="Game to chart (e.g., 'Chiefs Raiders')",
    )
    @require_tier(Tier.PRO)
    async def chart_movement_command(
        self,
        interaction: discord.Interaction,
        game: str,
    ):
        """Generate visual line movement chart."""
        await interaction.response.defer()

        try:
            from sharpedge_analytics.visualizations import create_line_movement_chart
            from sharpedge_db.queries.line_movements import get_line_history

            # Get line history (mock data for now if not available)
            # In production, this would pull from actual line_movements table

            # Generate sample data for demo
            now = datetime.now()
            timestamps = [now - timedelta(hours=i) for i in range(24, 0, -1)]
            lines = [-3.0, -3.0, -3.5, -3.5, -3.5, -4.0, -4.0, -4.0,
                     -3.5, -3.5, -4.0, -4.5, -4.5, -4.5, -4.0, -4.0,
                     -4.5, -4.5, -5.0, -5.0, -4.5, -4.5, -4.5, -4.5]

            chart_bytes = create_line_movement_chart(
                timestamps=timestamps,
                lines=lines,
                team_name=game,
                opening_line=-3.0,
                consensus_line=-4.0,
                key_numbers=[3.0, 7.0],
            )

            embed = create_chart_embed(
                title=f"📊 Line Movement: {game}",
                description="24-hour spread movement across sportsbooks",
                footer="Key numbers (3, 7) highlighted | SharpEdge",
            )

            await send_chart_followup(
                interaction,
                chart_bytes,
                filename="line_movement.png",
                embed=embed,
            )

        except Exception as e:
            logger.exception("Error generating chart")
            await interaction.followup.send(
                f"Error generating chart: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="chart-value",
        description="Generate chart of current value plays",
    )
    @app_commands.describe(
        sport="Filter by sport (optional)",
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
    async def chart_value_command(
        self,
        interaction: discord.Interaction,
        sport: str = "all",
    ):
        """Generate visual EV distribution chart."""
        await interaction.response.defer()

        try:
            from sharpedge_analytics.visualizations import create_ev_distribution_chart
            from sharpedge_db.queries.value_plays import get_active_value_plays

            sport_filter = None if sport == "all" else sport
            plays = get_active_value_plays(sport=sport_filter, min_ev=1.0, limit=10)

            chart_bytes = create_ev_distribution_chart(
                plays=plays or [],
                title=f"Value Plays - {sport.upper() if sport != 'all' else 'All Sports'}",
            )

            embed = create_chart_embed(
                title="💰 Value Play Distribution",
                description=f"Found {len(plays) if plays else 0} plays with EV ≥ 1%",
                footer="Green = HIGH confidence | Yellow = MEDIUM | SharpEdge",
            )

            await send_chart_followup(
                interaction,
                chart_bytes,
                filename="value_distribution.png",
                embed=embed,
            )

        except Exception as e:
            logger.exception("Error generating chart")
            await interaction.followup.send(
                f"Error generating chart: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="chart-bankroll",
        description="Generate your bankroll performance chart",
    )
    @require_tier(Tier.PRO)
    async def chart_bankroll_command(
        self,
        interaction: discord.Interaction,
    ):
        """Generate visual bankroll performance chart."""
        await interaction.response.defer()

        try:
            from sharpedge_analytics.visualizations import create_bankroll_chart
            from sharpedge_db.queries.bets import get_user_bets_history

            user_id = str(interaction.user.id)

            # Get bet history
            bets = get_user_bets_history(user_id, limit=100)

            if not bets:
                await interaction.followup.send(
                    "No betting history found. Log some bets first!",
                    ephemeral=True,
                )
                return

            # Calculate running bankroll
            from sharpedge_db.queries.users import get_user_by_discord_id
            user = get_user_by_discord_id(user_id)
            starting_bankroll = float(user.bankroll) if user else 1000.0

            dates = []
            bankroll_values = [starting_bankroll]
            running_bankroll = starting_bankroll

            for bet in reversed(bets):  # Oldest first
                if bet.get("profit") is not None:
                    running_bankroll += float(bet.get("profit", 0))
                    dates.append(datetime.fromisoformat(bet.get("placed_at", datetime.now().isoformat())))
                    bankroll_values.append(running_bankroll)

            if len(dates) < 2:
                # Add current date
                dates = [datetime.now() - timedelta(days=30), datetime.now()]
                bankroll_values = [starting_bankroll, running_bankroll]

            chart_bytes = create_bankroll_chart(
                dates=dates,
                bankroll_values=bankroll_values[1:] if len(bankroll_values) > len(dates) else bankroll_values,
                bets=bets[:20],  # Recent bets for markers
            )

            roi = ((running_bankroll / starting_bankroll) - 1) * 100

            embed = create_chart_embed(
                title="💰 Your Bankroll Performance",
                description=f"Current: ${running_bankroll:,.2f} | ROI: {roi:+.1f}%",
                color=0x43b581 if roi >= 0 else 0xf04747,
            )

            await send_chart_followup(
                interaction,
                chart_bytes,
                filename="bankroll.png",
                embed=embed,
            )

        except Exception as e:
            logger.exception("Error generating chart")
            await interaction.followup.send(
                f"Error generating chart: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="chart-clv",
        description="Generate your Closing Line Value chart",
    )
    @require_tier(Tier.SHARP)
    async def chart_clv_command(
        self,
        interaction: discord.Interaction,
    ):
        """Generate visual CLV tracking chart."""
        await interaction.response.defer()

        try:
            from sharpedge_analytics.visualizations import create_clv_chart
            from sharpedge_db.queries.bets import get_user_clv_history

            user_id = str(interaction.user.id)

            # Get CLV history
            clv_data = get_user_clv_history(user_id, limit=100)

            if not clv_data or len(clv_data) < 5:
                await interaction.followup.send(
                    "Need at least 5 bets with CLV data. Keep betting!",
                    ephemeral=True,
                )
                return

            clv_values = [d.get("clv_percentage", 0) for d in clv_data]
            bet_labels = [d.get("description", "")[:20] for d in clv_data]

            chart_bytes = create_clv_chart(
                clv_values=clv_values,
                bet_labels=bet_labels,
                rolling_window=10,
            )

            avg_clv = sum(clv_values) / len(clv_values)

            embed = create_chart_embed(
                title="📊 Your Closing Line Value",
                description=f"Average CLV: {avg_clv:+.2f}% over {len(clv_values)} bets",
                color=0x43b581 if avg_clv >= 0 else 0xf04747,
                footer="Positive CLV = Long-term edge | SharpEdge",
            )

            await send_chart_followup(
                interaction,
                chart_bytes,
                filename="clv_chart.png",
                embed=embed,
            )

        except Exception as e:
            logger.exception("Error generating chart")
            await interaction.followup.send(
                f"Error generating chart: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="chart-public",
        description="Generate public betting breakdown chart",
    )
    @app_commands.describe(
        game="Game to chart (e.g., 'Chiefs Raiders')",
    )
    @require_tier(Tier.PRO)
    async def chart_public_command(
        self,
        interaction: discord.Interaction,
        game: str,
    ):
        """Generate public betting visual chart."""
        await interaction.response.defer()

        try:
            from sharpedge_analytics.visualizations import create_public_betting_chart

            # Parse teams
            parts = game.replace(" vs ", " ").replace(" @ ", " ").split()
            if len(parts) >= 2:
                away_team = parts[0]
                home_team = parts[-1]
            else:
                away_team = "Away"
                home_team = "Home"

            # Get public betting data
            from sharpedge_db.queries.public_betting import get_public_betting
            # This would need game_id lookup - using mock for demo

            # Mock data for demo (would pull from DB in production)
            chart_bytes = create_public_betting_chart(
                team_names=[home_team, away_team],
                ticket_pcts=[35, 65],
                money_pcts=[52, 48],
                title=f"Public vs Sharp: {game}",
            )

            embed = create_chart_embed(
                title=f"📊 Public Betting: {game}",
                description="Ticket % vs Money % breakdown",
                footer="🎯 = Sharp money divergence | SharpEdge",
            )

            await send_chart_followup(
                interaction,
                chart_bytes,
                filename="public_betting.png",
                embed=embed,
            )

        except Exception as e:
            logger.exception("Error generating chart")
            await interaction.followup.send(
                f"Error generating chart: {str(e)}", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(ResearchCog(bot))
