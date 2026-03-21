"""Subscription commands: /subscribe, /manage, /tier."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from sharpedge_bot.services.subscription_service import get_whop_checkout_url
from sharpedge_db.queries.users import get_or_create_user
from sharpedge_shared.constants import COLOR_INFO, COLOR_PREMIUM

logger = logging.getLogger("sharpedge.commands.subscription")


class SubscriptionCog(commands.Cog, name="Subscription"):
    """Subscription management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="subscribe", description="Upgrade to SharpEdge Pro or Sharp")
    async def subscribe_command(self, interaction: discord.Interaction) -> None:
        config = self.bot.config  # type: ignore[attr-defined]

        # Check if Whop is configured
        if not config.whop_pro_product_id:
            await interaction.response.send_message(
                "Subscriptions are not configured yet. Stay tuned!",
                ephemeral=True,
            )
            return

        discord_id = str(interaction.user.id)
        user = get_or_create_user(discord_id, interaction.user.display_name)

        if user.tier in ("pro", "sharp"):
            await interaction.response.send_message(
                f"You're already a **{user.tier.title()}** member! Use `/manage` to manage your subscription.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="SharpEdge Subscription Plans",
            description="Choose your plan below. Powered by Whop.",
            color=COLOR_PREMIUM,
        )
        embed.add_field(
            name="Pro — $19.99/month",
            value=(
                "- Unlimited game analysis\n"
                "- Bet logging & performance tracking\n"
                "- +EV value scanner\n"
                "- Sharp money indicators\n"
                "- AI research assistant\n"
                "- Visual analytics charts\n"
                "- Line movement alerts\n"
                "- Prediction markets (Kalshi / Polymarket)"
            ),
            inline=True,
        )
        embed.add_field(
            name="Sharp — $49.99/month",
            value=(
                "- Everything in Pro\n"
                "- Sportsbook arbitrage scanner\n"
                "- CLV tracking\n"
                "- Weekly AI betting review\n"
                "- Priority support\n"
                "- Verified Sharp flair"
            ),
            inline=True,
        )

        # Create view with Whop checkout buttons
        view = SubscribeView(config, discord_id)

        embed.set_footer(text="Cancel anytime. Secure checkout via Whop.")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="tier", description="View your current subscription tier")
    async def tier_command(self, interaction: discord.Interaction) -> None:
        discord_id = str(interaction.user.id)
        user = get_or_create_user(discord_id, interaction.user.display_name)

        tier_info = {
            "free": (
                "Free",
                "Basic access to odds comparison and Kelly calculator.\n"
                "Use `/subscribe` to unlock Pro features!",
            ),
            "pro": (
                "Pro",
                "Full access to:\n"
                "- Bet tracking & stats\n"
                "- +EV value scanner\n"
                "- Sharp money indicators\n"
                "- AI research assistant\n"
                "- Visual charts\n"
                "- Line movement analysis",
            ),
            "sharp": (
                "Sharp",
                "Everything unlocked:\n"
                "- All Pro features\n"
                "- Sportsbook arbitrage scanner\n"
                "- CLV tracking\n"
                "- Weekly AI reviews\n"
                "- Priority support\n"
                "- Verified Sharp flair",
            ),
        }

        title, desc = tier_info.get(user.tier, ("Unknown", ""))

        color = COLOR_PREMIUM if user.tier in ("pro", "sharp") else COLOR_INFO

        embed = discord.Embed(
            title=f"Your Tier: {title}",
            description=desc,
            color=color,
        )

        if user.tier == "free":
            embed.add_field(
                name="Upgrade",
                value="Use `/subscribe` to unlock premium features!",
                inline=False,
            )
        elif user.tier == "pro":
            embed.add_field(
                name="Upgrade to Sharp",
                value="Use `/subscribe` for sportsbook arb, CLV, and weekly AI reviews!",
                inline=False,
            )

        embed.set_footer(text="SharpEdge")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="manage", description="Manage your subscription")
    async def manage_command(self, interaction: discord.Interaction) -> None:

        discord_id = str(interaction.user.id)
        user = get_or_create_user(discord_id, interaction.user.display_name)

        if user.tier == "free":
            await interaction.response.send_message(
                "You don't have an active subscription. Use `/subscribe` to get started!",
                ephemeral=True,
            )
            return

        # Whop manages subscriptions through their portal
        # Users can access their subscriptions at whop.com/orders
        embed = discord.Embed(
            title="Manage Your Subscription",
            description=(
                f"**Current Tier:** {user.tier.title()}\n\n"
                "To manage your subscription (cancel, update payment, etc.):\n\n"
                "1. Go to [whop.com/orders](https://whop.com/orders)\n"
                "2. Sign in with your Discord account\n"
                "3. Find your SharpEdge subscription\n"
                "4. Click 'Manage' to make changes"
            ),
            color=COLOR_INFO,
        )
        embed.set_footer(text="Subscription management powered by Whop")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class SubscribeView(discord.ui.View):
    """Button view for subscription checkout."""

    def __init__(self, config: object, discord_id: str) -> None:
        super().__init__(timeout=300)
        self.config = config
        self.discord_id = discord_id

        # Get checkout URLs
        company_slug = getattr(config, "whop_company_slug", "sharpedge")
        pro_product = getattr(config, "whop_pro_product_id", "")
        sharp_product = getattr(config, "whop_sharp_product_id", "")

        # Add URL buttons (these are link buttons, not interactive)
        if pro_product:
            pro_url = get_whop_checkout_url(pro_product, company_slug, discord_id)
            self.add_item(
                discord.ui.Button(
                    label="Subscribe Pro ($19.99/mo)",
                    style=discord.ButtonStyle.link,
                    url=pro_url,
                )
            )

        if sharp_product:
            sharp_url = get_whop_checkout_url(sharp_product, company_slug, discord_id)
            self.add_item(
                discord.ui.Button(
                    label="Subscribe Sharp ($49.99/mo)",
                    style=discord.ButtonStyle.link,
                    url=sharp_url,
                )
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SubscriptionCog(bot))
