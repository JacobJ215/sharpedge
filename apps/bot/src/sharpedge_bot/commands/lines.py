"""Lines command: /lines — Compare odds across sportsbooks."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_shared.errors import ExternalAPIError
from sharpedge_shared.types import Sport, Tier

from sharpedge_bot.commands.betting import SPORT_CHOICES
from sharpedge_bot.embeds.lines_embeds import enhanced_lines_embed, lines_embed
from sharpedge_bot.services.odds_service import get_lines_for_game

logger = logging.getLogger("sharpedge.commands.lines")


class LinesCog(commands.Cog, name="Lines"):
    """Odds comparison commands — available to all tiers."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="lines",
        description="Compare current lines across sportsbooks for a game",
    )
    @app_commands.describe(
        game='Game to look up (e.g., "Chiefs Raiders" or "KC vs LV")',
        sport="Sport (auto-detected if not specified)",
    )
    @app_commands.choices(sport=SPORT_CHOICES)
    async def lines_command(
        self,
        interaction: discord.Interaction,
        game: str,
        sport: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer()

        config = self.bot.config  # type: ignore[attr-defined]

        if not config.odds_api_key:
            await interaction.followup.send(
                "Odds API is not configured. Contact an admin.", ephemeral=True
            )
            return

        try:
            comparison = get_lines_for_game(
                game_query=game,
                api_key=config.odds_api_key,
                redis_url=config.redis_url,
                sport=Sport(sport.value) if sport else None,
            )
        except ExternalAPIError as e:
            await interaction.followup.send(
                f"Could not find odds for '{game}'. Try being more specific "
                f"(e.g., 'Chiefs Raiders' or 'Lakers Celtics').\n\nError: {e.detail}",
                ephemeral=True,
            )
            return

        # Check user tier for enhanced analytics
        from sharpedge_db.queries.users import get_user_by_discord_id

        user = get_user_by_discord_id(str(interaction.user.id))
        user_tier = user.tier if user else Tier.FREE

        # Pro/Sharp users get enhanced analytics
        if user_tier in (Tier.PRO, Tier.SHARP):
            embed = await self._build_enhanced_lines_embed(comparison)
        else:
            embed = lines_embed(comparison)

        await interaction.followup.send(embed=embed)

    async def _build_enhanced_lines_embed(
        self,
        comparison,
    ) -> discord.Embed:
        """Build enhanced lines embed with analytics for Pro/Sharp users."""
        from sharpedge_db.queries.consensus import get_consensus
        from sharpedge_db.queries.opening_lines import get_opening_line
        from sharpedge_db.queries.public_betting import get_public_betting

        game_id = comparison.game_id

        # Fetch analytics data
        consensus = get_consensus(game_id)
        opening = get_opening_line(game_id, bet_type="spread")
        public = get_public_betting(game_id)

        # Calculate no-vig probabilities from best lines
        no_vig = None
        try:
            from sharpedge_analytics import calculate_no_vig_odds

            no_vig_data = {}

            # Spread no-vig
            if comparison.spread_home and comparison.spread_away:
                best_home = next((l for l in comparison.spread_home if l.is_best), None)
                best_away = next((l for l in comparison.spread_away if l.is_best), None)
                if best_home and best_away:
                    home_prob, away_prob = calculate_no_vig_odds(best_home.odds, best_away.odds)
                    no_vig_data["spread_home_prob"] = home_prob
                    no_vig_data["spread_away_prob"] = away_prob

            # Moneyline no-vig
            if comparison.moneyline_home and comparison.moneyline_away:
                best_ml_home = next((l for l in comparison.moneyline_home if l.is_best), None)
                best_ml_away = next((l for l in comparison.moneyline_away if l.is_best), None)
                if best_ml_home and best_ml_away:
                    ml_home_prob, ml_away_prob = calculate_no_vig_odds(
                        best_ml_home.odds, best_ml_away.odds
                    )
                    no_vig_data["ml_home_prob"] = ml_home_prob
                    no_vig_data["ml_away_prob"] = ml_away_prob

            # Total no-vig
            if comparison.total_over and comparison.total_under:
                best_over = next((l for l in comparison.total_over if l.is_best), None)
                best_under = next((l for l in comparison.total_under if l.is_best), None)
                if best_over and best_under:
                    over_prob, under_prob = calculate_no_vig_odds(best_over.odds, best_under.odds)
                    no_vig_data["total_over_prob"] = over_prob
                    no_vig_data["total_under_prob"] = under_prob

            if no_vig_data:
                no_vig = no_vig_data
        except ImportError:
            # Analytics package not available
            pass

        return enhanced_lines_embed(
            comparison=comparison,
            consensus=consensus,
            opening=opening,
            public=public,
            no_vig=no_vig,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LinesCog(bot))
