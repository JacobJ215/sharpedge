"""Discord embed builders for stats and bankroll displays.

Institutional-grade visual formatting for professional presentation.
"""

from decimal import Decimal

import discord

from sharpedge_bot.utils.formatting import (
    format_record,
    format_units,
)
from sharpedge_db.models import (
    BankrollInfo,
    BetTypeBreakdown,
    CLVSummary,
    KellyResult,
    PerformanceSummary,
    SportBreakdown,
)
from sharpedge_shared.constants import COLOR_INFO, COLOR_SUCCESS

# ============================================
# VISUAL ENHANCEMENT UTILITIES
# ============================================


def _progress_bar(
    value: float, max_value: float = 100, width: int = 10, fill: str = "█", empty: str = "░"
) -> str:
    """Create a visual progress bar for Discord."""
    if max_value == 0:
        return empty * width
    ratio = min(max(value / max_value, 0), 1)
    filled = int(ratio * width)
    return fill * filled + empty * (width - filled)


def _trend_indicator(value: float, threshold: float = 0) -> str:
    """Return trend indicator emoji based on value."""
    if value > threshold + 2:
        return "📈"
    elif value > threshold:
        return "↗️"
    elif value < threshold - 2:
        return "📉"
    elif value < threshold:
        return "↘️"
    return "➡️"


def _calculate_roi_confidence_interval(
    wins: int,
    losses: int,
    units_won: float,
    confidence: float = 0.95,
) -> tuple[float, float] | None:
    """Calculate confidence interval for ROI using bootstrap approximation.

    Returns None if insufficient data for meaningful CI.
    """
    total = wins + losses
    if total < 20:
        return None  # Not enough data for reliable CI

    # Approximate ROI standard error
    # ROI variance depends on bet sizing and win/loss distribution
    # Using simplified formula: SE ≈ σ / sqrt(n)
    abs(units_won) / total if total > 0 else 1
    roi = (units_won / total) * 100 if total > 0 else 0

    # Approximate standard deviation of returns (typically 1-2 units per bet)
    estimated_std = 1.5  # Conservative estimate
    se = estimated_std / (total**0.5) * 100

    # 95% CI
    from scipy import stats

    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    ci_lower = roi - z * se
    ci_upper = roi + z * se

    return (round(ci_lower, 1), round(ci_upper, 1))


def _sample_size_indicator(n: int) -> str:
    """Indicate statistical reliability based on sample size."""
    if n >= 500:
        return "📊 Large sample (n≥500)"
    elif n >= 100:
        return "📈 Good sample (n≥100)"
    elif n >= 30:
        return "📉 Small sample (n≥30)"
    else:
        return "⚠️ Very small sample (n<30)"


def _win_rate_with_ci(wins: int, losses: int) -> str:
    """Return win rate with Wilson score confidence interval."""
    total = wins + losses
    if total == 0:
        return "N/A"

    win_rate = wins / total * 100

    if total < 10:
        return f"{win_rate:.1f}% (insufficient data for CI)"

    # Wilson score interval

    z = 1.96  # 95% CI
    p_hat = wins / total
    denominator = 1 + z**2 / total
    center = (p_hat + z**2 / (2 * total)) / denominator
    margin = z * ((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total) ** 0.5 / denominator

    ci_lower = max(0, center - margin) * 100
    ci_upper = min(1, center + margin) * 100

    return f"{win_rate:.1f}% (95% CI: {ci_lower:.0f}%-{ci_upper:.0f}%)"


def _win_rate_emoji(rate: float) -> str:
    """Emoji based on win rate."""
    if rate >= 60:
        return "🔥"
    elif rate >= 55:
        return "✅"
    elif rate >= 50:
        return "📊"
    elif rate >= 45:
        return "⚠️"
    return "❌"


def stats_overview_embed(
    summary: PerformanceSummary,
    by_sport: list[SportBreakdown],
    by_type: list[BetTypeBreakdown],
    clv: CLVSummary,
    period: str = "all",
) -> discord.Embed:
    """Build stats overview with statistically-grounded metrics."""
    period_label = {
        "all": "All Time",
        "today": "Today",
        "week": "Last 7 Days",
        "month": "Last 30 Days",
        "season": "This Season",
    }.get(period, period.title())

    # Dynamic color based on performance
    if summary.roi >= 5:
        color = 0x00FF7F  # Bright green
    elif summary.roi >= 0:
        color = COLOR_SUCCESS
    elif summary.roi >= -5:
        color = 0xFFA500  # Orange
    else:
        color = 0xFF4444  # Red

    embed = discord.Embed(
        title=f"📊 PERFORMANCE DASHBOARD — {period_label}",
        color=color,
    )

    if summary.total_bets == 0:
        embed.description = (
            "```\n"
            "┌─────────────────────────────────────┐\n"
            "│     No settled bets recorded yet    │\n"
            "│      Use /bet to start tracking     │\n"
            "└─────────────────────────────────────┘\n"
            "```"
        )
        return embed

    # Sample size indicator - critical for statistical reliability
    sample_indicator = _sample_size_indicator(summary.total_bets)
    trend = _trend_indicator(summary.roi)
    win_emoji = _win_rate_emoji(summary.win_rate)

    # Calculate ROI confidence interval
    roi_ci = _calculate_roi_confidence_interval(summary.wins, summary.losses, summary.units_won)

    # Summary with statistical context
    embed.description = (
        f"**Sample:** {summary.total_bets} bets • {sample_indicator}\n**Trend:** {trend} ROI"
    )

    # Main stats block with confidence intervals
    win_rate_display = _win_rate_with_ci(summary.wins, summary.losses)

    roi_display = f"{summary.roi:+.1f}%"
    if roi_ci:
        roi_display += f" (95% CI: {roi_ci[0]:+.1f}% to {roi_ci[1]:+.1f}%)"

    embed.add_field(
        name=f"{win_emoji} Overall Performance",
        value=(
            f"**Record:** {format_record(summary.wins, summary.losses, summary.pushes)}\n"
            f"**Win Rate:** {win_rate_display}\n"
            f"**Units:** {format_units(summary.units_won)}\n"
            f"**ROI:** {roi_display}"
        ),
        inline=False,
    )

    # Statistical reliability note for small samples
    if summary.total_bets < 100:
        embed.add_field(
            name="📋 Statistical Note",
            value=(
                f"*With {summary.total_bets} bets, results may be heavily influenced by variance. "
                f"100+ settled bets recommended for reliable performance assessment.*"
            ),
            inline=False,
        )

    # By sport with visual bars
    if by_sport:
        sport_lines = []
        max_units = max(abs(s.units_won) for s in by_sport) if by_sport else 1
        for s in by_sport[:5]:
            bar = _progress_bar(abs(s.units_won), max_units, 6)
            emoji = "🟢" if s.units_won > 0 else "🔴" if s.units_won < 0 else "⚪"
            n_bets = s.wins + s.losses
            sample_note = "" if n_bets >= 30 else " ⚠️"
            sport_lines.append(
                f"{emoji} **{s.sport}** `{bar}` {s.wins}-{s.losses} • {format_units(s.units_won)} • {s.roi:+.1f}%{sample_note}"
            )
        embed.add_field(
            name="📈 By Sport",
            value="\n".join(sport_lines) + "\n*⚠️ = small sample*"
            if any("⚠️" in row for row in sport_lines)
            else "\n".join(sport_lines),
            inline=False,
        )

    # By bet type
    if by_type:
        type_lines = []
        for t in by_type[:4]:
            emoji = "🟢" if t.units_won > 0 else "🔴" if t.units_won < 0 else "⚪"
            type_lines.append(
                f"{emoji} **{t.bet_type.title()}:** {t.wins}-{t.losses} ({format_units(t.units_won)}) — {t.roi:+.1f}%"
            )
        embed.add_field(
            name="🎯 By Bet Type",
            value="\n".join(type_lines),
            inline=True,
        )

    # CLV analysis - the most statistically meaningful metric
    if clv.positive_clv_count + clv.negative_clv_count > 0:
        total_clv_bets = clv.positive_clv_count + clv.negative_clv_count
        clv_bar = _progress_bar(clv.positive_clv_rate, 100, 8)

        # CLV is a better edge indicator than results
        if clv.avg_clv > 0.5 and total_clv_bets >= 50:
            edge_status = "✅ Consistent edge detected"
        elif clv.avg_clv > 0:
            edge_status = "📊 Positive signal (more data needed)"
        elif clv.avg_clv > -0.5:
            edge_status = "➡️ Near breakeven"
        else:
            edge_status = "⚠️ Review bet selection process"

        embed.add_field(
            name=f"🎲 CLV Analysis (n={total_clv_bets})",
            value=(
                f"**Avg CLV:** `{clv.avg_clv:+.2f} pts`\n"
                f"**Positive Rate:** [{clv_bar}] {clv.positive_clv_rate:.0f}%\n"
                f"**Assessment:** {edge_status}"
            ),
            inline=True,
        )

    embed.set_footer(text="SharpEdge Analytics • Confidence intervals assume independent bets")
    embed.timestamp = discord.utils.utcnow()
    return embed


def bankroll_embed(info: BankrollInfo) -> discord.Embed:
    """Build institutional-grade bankroll management embed."""
    embed = discord.Embed(
        title="💰 BANKROLL MANAGEMENT",
        description="Professional stake sizing based on Kelly criterion principles",
        color=COLOR_SUCCESS,
    )

    # Main metrics with visual hierarchy
    embed.add_field(
        name="📊 Current Position",
        value=(
            f"```\n"
            f"Bankroll:   ${info.bankroll:>12,.2f}\n"
            f"Unit (1%):  ${info.unit_size:>12,.2f}\n"
            f"Max (3%):   ${info.max_bet:>12,.2f}\n"
            f"```"
        ),
        inline=False,
    )

    # Stake sizing visual guide
    sizing_visual = []
    for label, amount in info.sizing_table.items():
        # Create visual stake indicator
        if "0.5u" in label:
            emoji = "🟡"
        elif "1u" in label:
            emoji = "🟢"
        elif "2u" in label:
            emoji = "🔵"
        elif "3u" in label:
            emoji = "🟣"
        else:
            emoji = "⚪"
        sizing_visual.append(f"{emoji} **{label}:** {amount}")

    embed.add_field(
        name="📐 Stake Sizing Matrix",
        value="\n".join(sizing_visual),
        inline=True,
    )

    # Risk management guidance
    embed.add_field(
        name="⚠️ Risk Guidelines",
        value=(
            "• **Standard bet:** 1u (1%)\n"
            "• **High confidence:** 2u (2%)\n"
            "• **Max bet cap:** 3u (3%)\n"
            "• Never chase losses"
        ),
        inline=True,
    )

    embed.set_footer(text="SharpEdge • Bankroll management is the foundation of long-term success")
    embed.timestamp = discord.utils.utcnow()
    return embed


def kelly_embed(result: KellyResult, bankroll: Decimal | None = None) -> discord.Embed:
    """Build institutional-grade Kelly criterion calculator embed."""
    embed = discord.Embed(
        title="🧮 KELLY CRITERION ANALYSIS",
        color=COLOR_INFO,
    )

    # Visual edge indicator
    edge_bar = _progress_bar(result.edge, 20, 10)
    edge_emoji = (
        "🟢"
        if result.edge >= 5
        else "🟡"
        if result.edge >= 2
        else "🔴"
        if result.edge > 0
        else "⛔"
    )

    embed.add_field(
        name="📊 Edge Analysis",
        value=(
            f"```\n"
            f"Market Implied:  {result.implied_prob:>6.1f}%\n"
            f"Your Estimate:   {result.true_prob:>6.1f}%\n"
            f"────────────────────────\n"
            f"Edge Size:       {result.edge:>+6.1f} pts\n"
            f"```\n"
            f"{edge_emoji} Edge Meter: [{edge_bar}]"
        ),
        inline=False,
    )

    if result.full_kelly <= 0:
        embed.add_field(
            name="⛔ Recommendation: NO BET",
            value=(
                "```diff\n"
                "- Edge is zero or negative\n"
                "- No mathematical advantage exists\n"
                "- Pass on this opportunity\n"
                "```"
            ),
            inline=False,
        )
        embed.color = 0xFF4444
        embed.set_footer(text="SharpEdge • Discipline is profitable")
        return embed

    # Kelly recommendations with visual indicators
    embed.add_field(
        name="📈 Kelly Stake Recommendations",
        value=(
            f"```\n"
            f"Full Kelly:     {result.full_kelly:>6.2f}% ← Maximum theoretical\n"
            f"Half Kelly:     {result.half_kelly:>6.2f}% ← RECOMMENDED\n"
            f"Quarter Kelly:  {result.quarter_kelly:>6.2f}% ← Conservative\n"
            f"```"
        ),
        inline=False,
    )

    if bankroll and bankroll > 0:
        full_amt = bankroll * result.full_kelly / 100
        half_amt = bankroll * result.half_kelly / 100
        quarter_amt = bankroll * result.quarter_kelly / 100

        embed.add_field(
            name=f"💵 Stake Amounts (${bankroll:,.0f} bankroll)",
            value=(
                f"```\n"
                f"Full Kelly:     ${full_amt:>10,.2f}\n"
                f"Half Kelly:     ${half_amt:>10,.2f}  ✓ OPTIMAL\n"
                f"Quarter Kelly:  ${quarter_amt:>10,.2f}\n"
                f"```"
            ),
            inline=False,
        )

    # Educational note
    embed.add_field(
        name="💡 Why Half Kelly?",
        value=(
            "Half Kelly balances growth with variance reduction. "
            "Full Kelly maximizes long-term growth but has extreme swings. "
            "Quarter Kelly is conservative for uncertain edges."
        ),
        inline=False,
    )

    embed.set_footer(text="SharpEdge • Kelly Criterion optimizes bankroll growth")
    embed.timestamp = discord.utils.utcnow()
    return embed
