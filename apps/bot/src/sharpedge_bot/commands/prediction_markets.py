"""Prediction market commands - Kalshi/Polymarket arbitrage and analysis."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.middleware.tier_check import require_tier
from sharpedge_shared.types import Tier

logger = logging.getLogger("sharpedge.commands.pm")


class PredictionMarketsCog(commands.Cog):
    """Commands for prediction market analysis and arbitrage."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="pm-arb",
        description="Show cross-platform prediction market arbitrage opportunities",
    )
    @app_commands.describe(
        min_profit="Minimum profit percentage (default: 0.5)",
    )
    @require_tier(Tier.SHARP)
    async def pm_arb_command(
        self,
        interaction: discord.Interaction,
        min_profit: float = 0.5,
    ):
        """Show active prediction market arbitrage opportunities."""
        await interaction.response.defer()

        from sharpedge_db.client import get_supabase_client

        client = get_supabase_client()

        # Get active arbs
        result = (
            client.table("pm_arbitrage_opportunities")
            .select("*")
            .eq("is_active", True)
            .gte("net_profit_pct", min_profit)
            .order("net_profit_pct", desc=True)
            .limit(10)
            .execute()
        )

        arbs = result.data or []

        if not arbs:
            embed = discord.Embed(
                title="Prediction Market Arbitrage",
                description="No active arbitrage opportunities found.",
                color=0x808080,
            )
            embed.add_field(
                name="What are PM Arbs?",
                value=(
                    "Cross-platform arbitrage finds price discrepancies\n"
                    "between Kalshi and Polymarket for the same event.\n\n"
                    "These opportunities are rare and short-lived (5-45 sec).\n"
                    "We scan every 2 minutes to catch them."
                ),
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="⚡ Prediction Market Arbitrage",
            description=f"Found **{len(arbs)}** opportunities with ≥{min_profit}% profit",
            color=0x00FF00,
        )

        for i, arb in enumerate(arbs[:5], 1):
            # Calculate sizing for $1000 stake
            net_profit = arb.get("net_profit_pct", 0)
            stake_yes = arb.get("stake_yes", 500)
            stake_no = arb.get("stake_no", 500)
            guaranteed = arb.get("guaranteed_return", 1000)

            resolution_risk = arb.get("resolution_risk", 0)
            risk_emoji = "🟢" if resolution_risk < 0.05 else "🟡" if resolution_risk < 0.15 else "🔴"

            embed.add_field(
                name=f"{i}. {arb.get('event_description', 'Unknown')[:50]}...",
                value=(
                    f"**{arb.get('buy_yes_platform', '').upper()}** YES @ ${arb.get('buy_yes_price', 0):.2f}\n"
                    f"**{arb.get('buy_no_platform', '').upper()}** NO @ ${arb.get('buy_no_price', 0):.2f}\n"
                    f"📈 Net Profit: **{net_profit:.2f}%**\n"
                    f"💵 $1000 → ${stake_yes:.0f} / ${stake_no:.0f} = **${guaranteed - 1000:.2f}** profit\n"
                    f"{risk_emoji} Resolution Risk: {resolution_risk*100:.1f}%"
                ),
                inline=False,
            )

        embed.set_footer(
            text="⚠️ PM arbs are time-sensitive! Verify prices before executing."
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="pm-markets",
        description="Search prediction markets across Kalshi and Polymarket",
    )
    @app_commands.describe(
        query="Search term (e.g., 'bitcoin', 'election', 'fed rate')",
    )
    @require_tier(Tier.PRO)
    async def pm_markets_command(
        self,
        interaction: discord.Interaction,
        query: str,
    ):
        """Search prediction markets across platforms."""
        await interaction.response.defer()

        config = self.bot.config  # type: ignore[attr-defined]
        kalshi_key = getattr(config, "kalshi_api_key", None)

        if not kalshi_key:
            await interaction.followup.send(
                "Prediction market APIs not configured.", ephemeral=True
            )
            return

        try:
            from sharpedge_feeds.kalshi_client import get_kalshi_client
            from sharpedge_feeds.polymarket_client import get_polymarket_client
            import asyncio

            kalshi_client = await get_kalshi_client(kalshi_key)
            polymarket_client = await get_polymarket_client()

            try:
                kalshi_results, poly_results = await asyncio.gather(
                    kalshi_client.search_markets(query, limit=5),
                    polymarket_client.search_markets(query, limit=5),
                )
            finally:
                await kalshi_client.close()
                await polymarket_client.close()

            embed = discord.Embed(
                title=f"🔮 Prediction Markets: \"{query}\"",
                color=0x9932CC,
            )

            # Kalshi results
            if kalshi_results:
                kalshi_text = ""
                for m in kalshi_results[:3]:
                    kalshi_text += f"• **{m.title[:40]}**\n"
                    kalshi_text += f"  YES: ${m.yes_ask:.2f} | NO: ${m.no_ask:.2f} | Vol: {m.volume_24h:,}\n"
                embed.add_field(
                    name="📊 Kalshi",
                    value=kalshi_text or "No results",
                    inline=False,
                )
            else:
                embed.add_field(name="📊 Kalshi", value="No results", inline=False)

            # Polymarket results
            if poly_results:
                poly_text = ""
                for m in poly_results[:3]:
                    poly_text += f"• **{m.question[:40]}**\n"
                    poly_text += f"  YES: ${m.yes_price:.2f} | Vol: ${m.volume_24h:,.0f}\n"
                embed.add_field(
                    name="🌐 Polymarket",
                    value=poly_text or "No results",
                    inline=False,
                )
            else:
                embed.add_field(name="🌐 Polymarket", value="No results", inline=False)

            # Check for potential arbs
            if kalshi_results and poly_results:
                embed.add_field(
                    name="💡 Tip",
                    value="Use `/pm-arb` to see active arbitrage opportunities",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.exception("Error searching prediction markets")
            await interaction.followup.send(
                f"Error searching markets: {str(e)}", ephemeral=True
            )

    @app_commands.command(
        name="pm-compare",
        description="Compare a specific event across Kalshi and Polymarket",
    )
    @app_commands.describe(
        event="Event description (e.g., 'Bitcoin 100k')",
    )
    @require_tier(Tier.PRO)
    async def pm_compare_command(
        self,
        interaction: discord.Interaction,
        event: str,
    ):
        """Compare pricing for an event across platforms."""
        await interaction.response.defer()

        from sharpedge_bot.jobs.prediction_market_scanner import get_multi_platform_events

        events = get_multi_platform_events()

        # Find matching event
        event_lower = event.lower()
        matched = None
        for e in events:
            if event_lower in e["description"].lower():
                matched = e
                break

        if not matched:
            embed = discord.Embed(
                title="Event Not Found",
                description=f"No cross-platform event matching '{event}' found.",
                color=0xFF6600,
            )
            embed.add_field(
                name="Try These",
                value="Search for events with `/pm-markets` first",
                inline=False,
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"🔍 Cross-Platform Comparison",
            description=matched["description"][:200],
            color=0x3498DB,
        )

        embed.add_field(
            name="Platforms",
            value=", ".join(p.value for p in matched["platforms"]),
            inline=True,
        )

        embed.add_field(
            name="Match Confidence",
            value=f"{matched['equivalence_confidence']*100:.0f}%",
            inline=True,
        )

        if matched.get("resolution_risk"):
            embed.add_field(
                name="⚠️ Resolution Risk",
                value=matched["resolution_risk"],
                inline=False,
            )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(PredictionMarketsCog(bot))
