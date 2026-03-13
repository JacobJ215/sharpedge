import logging

from discord.ext import commands

logger = logging.getLogger("sharpedge.events")


class OnReady(commands.Cog):
    """Handles the bot ready event."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logger.info("SharpEdge bot is online as %s (ID: %s)", self.bot.user, self.bot.user.id)
        logger.info("Connected to %d guild(s).", len(self.bot.guilds))

        for guild in self.bot.guilds:
            logger.info("  - %s (ID: %s, Members: %d)", guild.name, guild.id, guild.member_count)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnReady(bot))
