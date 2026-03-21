"""Discord embed builders for bet-related responses.

Institutional-grade formatting for professional bet tracking presentation.
"""

import discord

from sharpedge_bot.utils.formatting import format_money, format_odds, format_record, format_units
from sharpedge_db.models import Bet, PerformanceSummary
from sharpedge_shared.constants import COLOR_INFO, COLOR_SUCCESS, COLOR_WARNING


# Visual enhancement utilities
def _stake_indicator(units: float) -> str:
    """Return visual stake size indicator."""
    if units >= 3:
        return "🔴 MAX"
    elif units >= 2:
        return "🟠 HIGH"
    elif units >= 1:
        return "🟢 STD"
    return "🟡 SMALL"


def _odds_quality(odds: int) -> str:
    """Return odds quality indicator."""
    # Convert to implied probability and assess value
    100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

    # Check if likely on underdog or favorite
    if odds > 150:
        return "🎰 LONGSHOT"
    elif odds > 0:
        return "🎯 DOG"
    elif odds > -150:
        return "📊 CLOSE"
    else:
        return "🏆 CHALK"


def bet_logged_embed(bet: Bet) -> discord.Embed:
    """Build institutional-grade embed for a successfully logged bet."""
    stake_badge = _stake_indicator(bet.units)
    odds_badge = _odds_quality(bet.odds)

    embed = discord.Embed(
        title="✅ BET LOGGED SUCCESSFULLY",
        color=COLOR_SUCCESS,
    )

    # Main bet info in formatted block
    embed.add_field(
        name="📋 Bet Details",
        value=(
            f"```\n"
            f"Sport:        {bet.sport}\n"
            f"Game:         {bet.game[:40]}\n"
            f"Selection:    {bet.selection[:35]}\n"
            f"Odds:         {format_odds(bet.odds)}\n"
            f"```"
        ),
        inline=False,
    )

    # Financial details
    embed.add_field(
        name="💰 Stake Info",
        value=(
            f"**Size:** {bet.units}u ({stake_badge})\n"
            f"**Amount:** ${bet.stake:,.2f}\n"
            f"**To Win:** ${bet.potential_win:,.2f}"
        ),
        inline=True,
    )

    embed.add_field(
        name="📊 Classification",
        value=(f"**Odds Type:** {odds_badge}\n**ID:** `{bet.id[:8]}`"),
        inline=True,
    )

    if bet.sportsbook:
        embed.add_field(name="🏢 Book", value=bet.sportsbook, inline=True)

    if bet.notes:
        embed.add_field(
            name="📝 Notes",
            value=f"*{bet.notes}*",
            inline=False,
        )

    embed.set_footer(text="SharpEdge • React W/L/P when settled or use /result")
    embed.timestamp = discord.utils.utcnow()
    return embed


def result_embed(bet: Bet, summary: PerformanceSummary | None = None) -> discord.Embed:
    """Build institutional-grade embed for a bet result."""
    profit = bet.profit or 0

    if bet.result == "WIN":
        title = "🏆 BET WON"
        color = 0x00FF7F  # Bright green
        profit_display = f"+${abs(profit):,.2f}"
        emoji = "✅"
    elif bet.result == "LOSS":
        title = "❌ BET LOST"
        color = 0xFF4444  # Red
        profit_display = f"-${abs(profit):,.2f}"
        emoji = "📉"
    else:
        title = "➡️ BET PUSHED"
        color = COLOR_WARNING
        profit_display = "$0.00"
        emoji = "🔄"

    embed = discord.Embed(
        title=title,
        description=f"**{bet.selection}** • {format_odds(bet.odds)}",
        color=color,
    )

    # Result summary
    embed.add_field(
        name=f"{emoji} Result",
        value=(
            f"```diff\n"
            f"{'+ ' if bet.result == 'WIN' else '- ' if bet.result == 'LOSS' else '  '}{profit_display}\n"
            f"```"
        ),
        inline=True,
    )

    embed.add_field(
        name="📋 Bet ID",
        value=f"`{bet.id[:8]}`",
        inline=True,
    )

    # Updated performance stats
    if summary and summary.total_bets > 0:
        # Calculate session performance indicator
        if summary.roi > 5:
            perf_emoji = "🔥"
        elif summary.roi > 0:
            perf_emoji = "📈"
        elif summary.roi > -5:
            perf_emoji = "📊"
        else:
            perf_emoji = "⚠️"

        embed.add_field(
            name=f"{perf_emoji} Season Stats",
            value=(
                f"```\n"
                f"Record:    {format_record(summary.wins, summary.losses, summary.pushes)}\n"
                f"Win Rate:  {summary.win_rate:.1f}%\n"
                f"Units:     {format_units(summary.units_won)}\n"
                f"ROI:       {summary.roi:+.1f}%\n"
                f"```"
            ),
            inline=False,
        )

    embed.set_footer(text="SharpEdge • Tracking your edge")
    embed.timestamp = discord.utils.utcnow()
    return embed


def pending_embed(bets: list[Bet]) -> discord.Embed:
    """Build institutional-grade embed showing pending bets."""
    if not bets:
        embed = discord.Embed(
            title="📋 PENDING BETS",
            description=(
                "```\n"
                "┌─────────────────────────────────────┐\n"
                "│       No pending bets active        │\n"
                "│         Use /bet to log one         │\n"
                "└─────────────────────────────────────┘\n"
                "```"
            ),
            color=COLOR_INFO,
        )
        return embed

    # Calculate total exposure
    total_stake = sum(b.stake for b in bets)
    total_potential = sum(b.potential_win for b in bets)

    embed = discord.Embed(
        title=f"📋 PENDING BETS ({len(bets)} active)",
        color=COLOR_INFO,
    )

    # Exposure summary
    embed.add_field(
        name="💰 Exposure Summary",
        value=(f"**At Risk:** ${total_stake:,.2f}\n**Potential Win:** ${total_potential:,.2f}"),
        inline=False,
    )

    # Format bets in a table-like structure
    lines = []
    for bet in bets[:20]:  # Limit for display
        odds_str = format_odds(bet.odds)
        line = (
            f"`{bet.id[:8]}` │ **{bet.sport}** │ {bet.selection[:20]} │ {odds_str} │ {bet.units}u"
        )
        lines.append(line)

    if lines:
        embed.add_field(
            name="📊 Active Positions",
            value="\n".join(lines),
            inline=False,
        )

    if len(bets) > 20:
        embed.add_field(
            name="\u200b",
            value=f"*...and {len(bets) - 20} more bets*",
            inline=False,
        )

    embed.set_footer(text="SharpEdge • Use /result [id] [W/L/P] to record outcomes")
    embed.timestamp = discord.utils.utcnow()
    return embed


def history_embed(bets: list[Bet], page: int = 1, total: int | None = None) -> discord.Embed:
    """Build institutional-grade embed showing bet history."""
    if not bets:
        embed = discord.Embed(
            title="📜 BET HISTORY",
            description=("```\nNo bets found for this filter.\n```"),
            color=COLOR_INFO,
        )
        return embed

    embed = discord.Embed(
        title="📜 BET HISTORY",
        color=COLOR_INFO,
    )

    # Summary stats for this page
    page_wins = sum(1 for b in bets if b.result == "WIN")
    page_losses = sum(1 for b in bets if b.result == "LOSS")
    page_profit = sum(b.profit or 0 for b in bets if b.profit is not None)

    embed.description = (
        f"**Page Summary:** {page_wins}W-{page_losses}L • "
        f"P/L: {'+' if page_profit >= 0 else ''}{format_money(page_profit)}"
    )

    lines = []
    for bet in bets:
        result_icons = {
            "WIN": "🟢",
            "LOSS": "🔴",
            "PUSH": "⚪",
            "PENDING": "🟡",
        }
        icon = result_icons.get(bet.result, "❓")

        profit_str = format_money(bet.profit) if bet.profit is not None else "*pending*"
        line = (
            f"{icon} **{bet.sport}** │ {bet.selection[:25]} │ "
            f"{format_odds(bet.odds)} │ {bet.units}u │ {profit_str}"
        )
        lines.append(line)

    embed.add_field(
        name="📊 Bets",
        value="\n".join(lines) if lines else "No data",
        inline=False,
    )

    total_pages = (total // 10 + 1) if total else "?"
    embed.set_footer(text=f"Page {page} of {total_pages} • SharpEdge")
    embed.timestamp = discord.utils.utcnow()
    return embed
