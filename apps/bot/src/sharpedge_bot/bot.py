import logging

import discord
from discord.ext import commands

from sharpedge_bot.config import BotConfig

logger = logging.getLogger("sharpedge")


class SharpEdgeBot(commands.Bot):
    """Main bot class for SharpEdge."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config

        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",  # Slash commands are primary, prefix as fallback
            intents=intents,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="lines move | /help",
            ),
            status=discord.Status.online,
        )

    async def setup_hook(self) -> None:
        """Load all cogs and sync commands on startup."""
        # Load event handlers
        await self.load_extension("sharpedge_bot.events.on_ready")
        await self.load_extension("sharpedge_bot.events.on_member_join")

        # Load command cogs
        await self.load_extension("sharpedge_bot.commands.betting")
        await self.load_extension("sharpedge_bot.commands.stats")
        await self.load_extension("sharpedge_bot.commands.bankroll")
        await self.load_extension("sharpedge_bot.commands.lines")
        await self.load_extension("sharpedge_bot.commands.subscription")
        await self.load_extension("sharpedge_bot.commands.analysis")
        await self.load_extension("sharpedge_bot.commands.review")
        await self.load_extension("sharpedge_bot.commands.value")
        await self.load_extension("sharpedge_bot.commands.market")
        await self.load_extension("sharpedge_bot.commands.prediction_markets")
        await self.load_extension("sharpedge_bot.commands.research")

        logger.info("All extensions loaded.")

        # Sync commands to the guild for faster updates during development
        guild = discord.Object(id=int(self.config.discord_guild_id))
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        logger.info("Slash commands synced to guild %s.", self.config.discord_guild_id)

        # Start background jobs (odds monitoring, alerts)
        from sharpedge_bot.jobs.scheduler import start_scheduler

        start_scheduler(self)
        logger.info("Background scheduler started.")
