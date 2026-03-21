"""Discord embed builders for lines/odds comparison."""

import discord

from sharpedge_bot.utils.formatting import format_odds
from sharpedge_odds.models import FormattedLine, LineComparison
from sharpedge_shared.constants import COLOR_INFO


def lines_embed(
    comparison: LineComparison,
    analytics: dict | None = None,
) -> discord.Embed:
    """Build the line comparison embed for a game.

    Args:
        comparison: Line comparison data from odds service
        analytics: Optional analytics data (consensus, opening, etc.)
    """
    time_str = f"<t:{int(comparison.commence_time.timestamp())}:F>"

    embed = discord.Embed(
        title=f"LINE COMPARISON — {comparison.away_team} @ {comparison.home_team}",
        description=time_str,
        color=COLOR_INFO,
    )

    # Add analytics summary if available
    if analytics:
        summary = _build_analytics_summary(analytics, comparison)
        if summary:
            embed.add_field(
                name="📊 Market Intelligence",
                value=summary,
                inline=False,
            )

    # Spreads
    if comparison.spread_home:
        home_lines = _format_spread_lines(comparison.spread_home)
        embed.add_field(
            name=f"Spread: {comparison.home_team}",
            value=home_lines or "N/A",
            inline=True,
        )

    if comparison.spread_away:
        away_lines = _format_spread_lines(comparison.spread_away)
        embed.add_field(
            name=f"Spread: {comparison.away_team}",
            value=away_lines or "N/A",
            inline=True,
        )

    # Blank field for spacing
    if comparison.spread_home or comparison.spread_away:
        embed.add_field(name="\u200b", value="\u200b", inline=True)

    # Totals
    if comparison.total_over:
        over_lines = _format_total_lines(comparison.total_over)
        embed.add_field(name="Over", value=over_lines or "N/A", inline=True)

    if comparison.total_under:
        under_lines = _format_total_lines(comparison.total_under)
        embed.add_field(name="Under", value=under_lines or "N/A", inline=True)

    if comparison.total_over or comparison.total_under:
        embed.add_field(name="\u200b", value="\u200b", inline=True)

    # Moneylines
    if comparison.moneyline_home:
        ml_home = _format_ml_lines(comparison.moneyline_home)
        embed.add_field(
            name=f"ML: {comparison.home_team}",
            value=ml_home or "N/A",
            inline=True,
        )

    if comparison.moneyline_away:
        ml_away = _format_ml_lines(comparison.moneyline_away)
        embed.add_field(
            name=f"ML: {comparison.away_team}",
            value=ml_away or "N/A",
            inline=True,
        )

    # Add no-vig probabilities if available
    if analytics and analytics.get("no_vig"):
        no_vig = analytics["no_vig"]
        embed.add_field(
            name="📈 Fair Odds (No-Vig)",
            value=(
                f"Spread: {comparison.home_team} {no_vig.get('spread_home_prob', 0) * 100:.1f}% | "
                f"{comparison.away_team} {no_vig.get('spread_away_prob', 0) * 100:.1f}%\n"
                f"ML: {comparison.home_team} {no_vig.get('ml_home_prob', 0) * 100:.1f}% | "
                f"{comparison.away_team} {no_vig.get('ml_away_prob', 0) * 100:.1f}%"
            ),
            inline=False,
        )

    footer_text = "* = Best available line"
    if analytics:
        footer_text += " | 📊 = Analytics available"
    footer_text += " | SharpEdge"

    embed.set_footer(text=footer_text)
    return embed


def _build_analytics_summary(analytics: dict, comparison: LineComparison) -> str:
    """Build analytics summary section."""
    parts = []

    # Consensus line
    if analytics.get("consensus"):
        consensus = analytics["consensus"]
        spread_consensus = consensus.get("spread_consensus")
        if spread_consensus is not None:
            parts.append(f"**Consensus:** {comparison.home_team} {spread_consensus:+.1f}")

    # Opening line movement
    if analytics.get("opening"):
        opening = analytics["opening"]
        opening_line = opening.get("opening_line")
        current_line = analytics.get("current_spread")

        if opening_line is not None and current_line is not None:
            movement = current_line - opening_line
            if abs(movement) >= 0.5:
                direction = "⬇️" if movement < 0 else "⬆️"
                parts.append(f"**Opened:** {opening_line:+.1f} {direction} {abs(movement):.1f} pts")

    # Public betting
    if analytics.get("public"):
        public = analytics["public"]
        ticket_home = public.get("spread_ticket_home", 50)
        if ticket_home >= 60 or ticket_home <= 40:
            public_side = comparison.home_team if ticket_home >= 50 else comparison.away_team
            public_pct = ticket_home if ticket_home >= 50 else (100 - ticket_home)
            parts.append(f"**Public:** {public_pct:.0f}% on {public_side}")

    # Sharp indicator
    if analytics.get("sharp_side"):
        sharp = analytics["sharp_side"]
        if sharp.get("signal") in ["STRONG", "MODERATE"]:
            parts.append(f"🎯 **Sharp money:** {sharp.get('side', 'Unknown')}")

    # Key number warning
    if analytics.get("key_number"):
        key = analytics["key_number"]
        if key.get("crosses_key"):
            parts.append(f"⚠️ Near key number **{key.get('nearest_key')}**")

    return "\n".join(parts) if parts else ""


def _format_spread_lines(lines: list[FormattedLine]) -> str:
    """Format spread lines for display."""
    # Sort by odds (best first)
    sorted_lines = sorted(lines, key=lambda fl: fl.odds, reverse=True)
    output = []
    for line in sorted_lines[:6]:
        point_str = f"{line.line:+.1f}" if line.line is not None else "PK"
        star = " **BEST**" if line.is_best else ""
        output.append(
            f"`{line.sportsbook_display:<12}` {point_str} ({format_odds(line.odds)}){star}"
        )
    return "\n".join(output)


def _format_total_lines(lines: list[FormattedLine]) -> str:
    """Format total lines for display."""
    sorted_lines = sorted(lines, key=lambda fl: fl.odds, reverse=True)
    output = []
    for line in sorted_lines[:6]:
        point_str = f"{line.line:.1f}" if line.line is not None else "?"
        star = " **BEST**" if line.is_best else ""
        output.append(
            f"`{line.sportsbook_display:<12}` {point_str} ({format_odds(line.odds)}){star}"
        )
    return "\n".join(output)


def _format_ml_lines(lines: list[FormattedLine]) -> str:
    """Format moneyline lines for display."""
    sorted_lines = sorted(lines, key=lambda fl: fl.odds, reverse=True)
    output = []
    for line in sorted_lines[:6]:
        star = " **BEST**" if line.is_best else ""
        output.append(f"`{line.sportsbook_display:<12}` {format_odds(line.odds)}{star}")
    return "\n".join(output)


def enhanced_lines_embed(
    comparison: LineComparison,
    consensus: dict | None = None,
    opening: dict | None = None,
    public: dict | None = None,
    no_vig: dict | None = None,
) -> discord.Embed:
    """Build enhanced line comparison embed with full analytics.

    This is the Pro/Sharp version with all available data.
    """
    analytics = {}

    if consensus:
        analytics["consensus"] = consensus

    if opening:
        analytics["opening"] = opening
        # Get current spread for movement calculation
        if comparison.spread_home:
            best_home = next((q for q in comparison.spread_home if q.is_best), None)
            if best_home:
                analytics["current_spread"] = best_home.line

    if public:
        analytics["public"] = public
        # Detect sharp side
        spread_ticket_home = public.get("spread_ticket_home", 50)
        spread_money_home = public.get("spread_money_home", 50)
        divergence = abs(spread_money_home - spread_ticket_home)

        if divergence >= 10:
            sharp_side = "home" if spread_money_home > spread_ticket_home else "away"
            analytics["sharp_side"] = {
                "side": comparison.home_team if sharp_side == "home" else comparison.away_team,
                "signal": "STRONG" if divergence >= 15 else "MODERATE",
                "divergence": divergence,
            }

    if no_vig:
        analytics["no_vig"] = no_vig

    # Check key numbers for spreads
    if comparison.spread_home:
        best_home = next((q for q in comparison.spread_home if q.is_best), None)
        if best_home and best_home.line is not None:
            from sharpedge_analytics import analyze_key_numbers

            key_analysis = analyze_key_numbers(best_home.line, "NFL")
            analytics["key_number"] = {
                "nearest_key": key_analysis.nearest_key,
                "distance": key_analysis.distance_to_key,
                "crosses_key": key_analysis.crosses_key,
            }

    return lines_embed(comparison, analytics)
