"""Background job: Dispatch alerts to Discord channels."""

import logging
import os

import discord

from sharpedge_bot.embeds.analysis_embeds import movement_alert_embed, value_alert_embed
from sharpedge_bot.jobs.odds_monitor import get_pending_alerts
from sharpedge_bot.jobs.value_scanner_job import get_pending_value_alerts
from sharpedge_bot.jobs.arbitrage_scanner import get_pending_arb_alerts

logger = logging.getLogger("sharpedge.jobs.alert_dispatcher")


async def dispatch_alerts(bot: object) -> None:
    """Process pending alerts and deliver to Discord channels.

    Handles three types of alerts:
    1. Line movement alerts (from odds_monitor)
    2. Value play alerts (from value_scanner)
    3. Arbitrage alerts (from arb_scanner)
    """
    # Get all pending alerts
    movement_alerts = get_pending_alerts()
    value_alerts = get_pending_value_alerts()
    arb_alerts = get_pending_arb_alerts()

    total_alerts = len(movement_alerts) + len(value_alerts) + len(arb_alerts)
    if total_alerts == 0:
        return

    # Channel IDs from environment
    movement_channel_id = os.environ.get("LINE_MOVEMENT_CHANNEL_ID", "")
    value_channel_id = os.environ.get("VALUE_ALERTS_CHANNEL_ID", "")
    arb_channel_id = os.environ.get("ARB_ALERTS_CHANNEL_ID", "") or value_channel_id

    delivered = 0

    # Dispatch movement alerts
    for alert in movement_alerts:
        try:
            if movement_channel_id:
                channel = bot.get_channel(int(movement_channel_id))  # type: ignore[attr-defined]
                if channel:
                    old_line = alert["old_line"]
                    new_line = alert["new_line"]
                    direction = "up" if new_line > old_line else "down"

                    embed = movement_alert_embed(
                        game=alert["game"],
                        old_line=old_line,
                        new_line=new_line,
                        direction=f"{'⬆' if direction == 'up' else '⬇'} {abs(new_line - old_line):.1f} pts",
                        interpretation=_interpret_movement(direction, alert),
                    )
                    await channel.send(embed=embed)
                    delivered += 1

        except Exception:
            logger.exception("Failed to deliver movement alert: %s", alert.get("game", "?"))

    # Dispatch value play alerts
    for play in value_alerts:
        try:
            if value_channel_id:
                channel = bot.get_channel(int(value_channel_id))  # type: ignore[attr-defined]
                if channel:
                    embed = _create_value_play_embed(play)
                    await channel.send(embed=embed)
                    delivered += 1

        except Exception:
            logger.exception("Failed to deliver value alert: %s", getattr(play, "game", "?"))

    # Dispatch arbitrage alerts
    for arb in arb_alerts:
        try:
            if arb_channel_id:
                channel = bot.get_channel(int(arb_channel_id))  # type: ignore[attr-defined]
                if channel:
                    embed = _create_arb_embed(arb)
                    await channel.send(embed=embed)
                    delivered += 1

        except Exception:
            logger.exception("Failed to deliver arb alert: %s", arb.get("game", "?"))

    if delivered:
        logger.info("Delivered %d/%d alerts.", delivered, total_alerts)


def _interpret_movement(direction: str, alert: dict) -> str:
    """Generate an interpretation of line movement."""
    movement = alert.get("movement", 0)
    if movement >= 1.0:
        return "Significant steam move detected. Sharp money likely involved."
    if movement >= 0.5:
        return "Notable line movement. Monitor for further changes."
    return ""


def _create_value_play_embed(play) -> discord.Embed:
    """Create embed for a value play alert."""
    # Determine color based on confidence
    if play.confidence == "HIGH":
        color = 0x00FF00  # Green
        confidence_emoji = "🟢"
    elif play.confidence == "MEDIUM":
        color = 0xFFFF00  # Yellow
        confidence_emoji = "🟡"
    else:
        color = 0xFFA500  # Orange
        confidence_emoji = "🟠"

    embed = discord.Embed(
        title=f"💰 Value Play Detected",
        description=f"**{play.game}**",
        color=color,
    )

    # Format odds
    odds_str = f"+{play.market_odds}" if play.market_odds > 0 else str(play.market_odds)

    embed.add_field(
        name="Selection",
        value=f"**{play.side}**\n{play.sportsbook}",
        inline=True,
    )

    embed.add_field(
        name="Odds",
        value=odds_str,
        inline=True,
    )

    embed.add_field(
        name="Expected Value",
        value=f"**+{play.ev_percentage:.1f}%**",
        inline=True,
    )

    embed.add_field(
        name="Edge",
        value=f"{play.edge_percentage:.1f}%",
        inline=True,
    )

    embed.add_field(
        name="Confidence",
        value=f"{confidence_emoji} {play.confidence}",
        inline=True,
    )

    embed.add_field(
        name="Model Prob",
        value=f"{play.model_probability * 100:.1f}%",
        inline=True,
    )

    embed.set_footer(text=f"Sport: {play.sport} | Bet Type: {play.bet_type}")

    return embed


def _create_arb_embed(arb: dict) -> discord.Embed:
    """Create embed for an arbitrage alert."""
    embed = discord.Embed(
        title=f"⚡ Arbitrage Opportunity",
        description=f"**{arb['game']}** | {arb['sport']}",
        color=0x00FF00,  # Green for guaranteed profit
    )

    # Format odds
    odds_a = f"+{arb['odds_a']}" if arb['odds_a'] > 0 else str(arb['odds_a'])
    odds_b = f"+{arb['odds_b']}" if arb['odds_b'] > 0 else str(arb['odds_b'])

    embed.add_field(
        name=f"Side A: {arb['book_a']}",
        value=f"**{arb['side_a']}**\n{odds_a} ({arb['stake_a_percentage']:.1f}% stake)",
        inline=True,
    )

    embed.add_field(
        name=f"Side B: {arb['book_b']}",
        value=f"**{arb['side_b']}**\n{odds_b} ({arb['stake_b_percentage']:.1f}% stake)",
        inline=True,
    )

    embed.add_field(
        name="Guaranteed Profit",
        value=f"**{arb['profit_percentage']:.2f}%**",
        inline=False,
    )

    # Example with $1000 stake
    example_profit = arb['profit_percentage'] * 10  # $1000 stake
    embed.add_field(
        name="Example ($1000 total)",
        value=(
            f"${arb['stake_a_percentage'] * 10:.2f} on {arb['book_a']}\n"
            f"${arb['stake_b_percentage'] * 10:.2f} on {arb['book_b']}\n"
            f"**Profit: ${example_profit:.2f}**"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Bet Type: {arb['bet_type']} | Act fast - arbs disappear quickly!")

    return embed
