import logging

import discord
from discord.ext import commands

from sharpedge_db.queries.users import get_or_create_user
from sharpedge_shared.constants import COLOR_INFO

logger = logging.getLogger("sharpedge.events")


class OnMemberJoin(commands.Cog):
    """Handles new member joins."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        logger.info("New member joined: %s (ID: %s)", member.name, member.id)

        # Create user record in database
        get_or_create_user(str(member.id), member.name)

        # Assign Free Member role if configured
        config = self.bot.config  # type: ignore[attr-defined]
        if config.free_role_id:
            role = member.guild.get_role(int(config.free_role_id))
            if role:
                await member.add_roles(role)
                logger.info("Assigned @Free Member role to %s.", member.name)

        # Send welcome DM
        try:
            embed = discord.Embed(
                title="Welcome to SharpEdge!",
                description=(
                    "Thanks for joining the SharpEdge community. Here's how to get started:"
                ),
                color=COLOR_INFO,
            )
            embed.add_field(
                name="Free Features",
                value=(
                    "- `/analyze [game]` — 3 free analyses per day\n"
                    "- `/lines [game]` — Compare odds across sportsbooks\n"
                    "- `/kelly [odds] [prob]` — Kelly criterion calculator"
                ),
                inline=False,
            )
            embed.add_field(
                name="Upgrade to Pro ($19.99/mo)",
                value=(
                    "- Unlimited game analysis\n"
                    "- Bet logging & performance tracking\n"
                    "- Value alerts & line movement alerts\n"
                    "- Prediction markets & web/mobile app access\n\n"
                    "Use `/subscribe` to upgrade!"
                ),
                inline=False,
            )
            embed.set_footer(text="SharpEdge — Be the sharp your bookie fears.")
            await member.send(embed=embed)
        except discord.Forbidden:
            logger.info("Could not DM %s (DMs disabled).", member.name)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OnMemberJoin(bot))
