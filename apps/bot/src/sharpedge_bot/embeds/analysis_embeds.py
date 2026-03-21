"""Discord embed builders for analysis and review outputs.

Institutional-grade formatting for professional presentation.
"""

import discord

from sharpedge_shared.constants import COLOR_INFO, COLOR_SUCCESS


# Visual enhancement utilities
def _confidence_badge(confidence: str, prob_edge: float | None = None) -> str:
    """Return visual confidence badge based on P(edge > 0).

    Confidence levels are statistically grounded:
    - PREMIUM: P(edge > 0) >= 95% (2σ confidence)
    - HIGH: P(edge > 0) >= 84% (1σ confidence)
    - MEDIUM: P(edge > 0) >= 70%
    - LOW: P(edge > 0) >= 55%
    - SPECULATIVE: P(edge > 0) < 55%
    """
    badges = {
        "PREMIUM": "🟢 95%+ CONF",
        "HIGH": "🟢 84%+ CONF",
        "MEDIUM": "🟡 70%+ CONF",
        "LOW": "🟠 55%+ CONF",
        "SPECULATIVE": "🔴 <55% CONF",
    }
    base_badge = badges.get(confidence.upper(), "⚪ UNKNOWN")

    # Add actual probability if provided
    if prob_edge is not None:
        return f"{base_badge} ({prob_edge:.0%})"
    return base_badge


def _calibration_indicator(is_calibrated: bool) -> str:
    """Return calibration status indicator."""
    if is_calibrated:
        return "✓ Backtested"
    return "⚠ Theoretical"


def _ev_tier_indicator(ev_pct: float, prob_edge: float | None = None) -> tuple[str, int]:
    """Return tier indicator and color based on statistical confidence.

    Uses P(edge > 0) if available, otherwise falls back to EV%.
    """
    # If we have the actual probability, use that
    if prob_edge is not None:
        if prob_edge >= 0.95:
            return "🔥 PREMIUM (95%+ conf)", 0x00FF7F
        elif prob_edge >= 0.84:
            return "✅ HIGH CONF (84%+)", 0x43B581
        elif prob_edge >= 0.70:
            return "📊 MODERATE (70%+)", 0x7289DA
        elif prob_edge >= 0.55:
            return "🔍 LOW CONF (55%+)", 0xFFA500
        else:
            return "⚠️ SPECULATIVE (<55%)", 0x99AAB5

    # Fallback to EV-based (less reliable)
    if ev_pct >= 5.0:
        return "🔥 HIGH EV", 0x00FF7F
    elif ev_pct >= 3.0:
        return "✅ GOOD EV", 0x43B581
    elif ev_pct >= 1.5:
        return "📊 MODERATE EV", 0x7289DA
    else:
        return "🔍 MARGINAL EV", 0x99AAB5


def analysis_embed(game_query: str, analysis_text: str) -> discord.Embed:
    """Build institutional-grade embed for game analysis."""
    embed = discord.Embed(
        title="🎯 GAME ANALYSIS",
        description=f"**{game_query.upper()}**",
        color=COLOR_INFO,
    )

    # Header decoration
    embed.add_field(
        name="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        value="*Powered by GPT-5 Research Agent*",
        inline=False,
    )

    # Split long text into multiple fields (Discord limit: 1024 per field)
    chunks = _split_text(analysis_text, 1000)
    for i, chunk in enumerate(chunks):
        name = "📋 Analysis" if i == 0 else "\u200b"
        embed.add_field(name=name, value=chunk, inline=False)

    embed.set_footer(text="SharpEdge Game Analyst • AI-Powered Analysis • Not financial advice")
    embed.timestamp = discord.utils.utcnow()
    return embed


def value_plays_embed(plays_text: str) -> discord.Embed:
    """Build institutional-grade embed for value plays."""
    embed = discord.Embed(
        title="⚡ VALUE SCANNER RESULTS",
        description="*Positive expected value opportunities identified*",
        color=COLOR_SUCCESS,
    )

    chunks = _split_text(plays_text, 1000)
    for i, chunk in enumerate(chunks):
        name = "📈 Active Opportunities" if i == 0 else "\u200b"
        embed.add_field(name=name, value=chunk, inline=False)

    embed.set_footer(text="SharpEdge • Value opportunities change rapidly — verify current lines")
    embed.timestamp = discord.utils.utcnow()
    return embed


def review_embed(title: str, review_text: str) -> discord.Embed:
    """Build institutional-grade embed for performance reviews."""
    embed = discord.Embed(
        title=f"📊 {title.upper()}",
        description="*Personalized performance analysis*",
        color=COLOR_INFO,
    )

    chunks = _split_text(review_text, 1000)
    for i, chunk in enumerate(chunks):
        name = "📋 Insights" if i == 0 else "\u200b"
        embed.add_field(name=name, value=chunk, inline=False)

    embed.set_footer(text="SharpEdge Review Agent • AI-Powered Insights • Not financial advice")
    embed.timestamp = discord.utils.utcnow()
    return embed


def value_alert_embed(
    game: str,
    side: str,
    odds: int,
    ev_pct: float,
    edge: float,
    model_line: float,
    market_line: float,
    confidence: str,
    prob_edge_positive: float | None = None,
    ci_lower: float | None = None,
    ci_upper: float | None = None,
    is_calibrated: bool = False,
    calibration_note: str | None = None,
) -> discord.Embed:
    """Build statistically-grounded value alert embed.

    Args:
        game: Game description
        side: Selection/pick
        odds: American odds
        ev_pct: Expected value percentage
        edge: Edge in probability points
        model_line: Model's projected line
        market_line: Current market line
        confidence: Confidence level (PREMIUM/HIGH/MEDIUM/LOW/SPECULATIVE)
        prob_edge_positive: P(true_edge > 0) - the statistical confidence
        ci_lower: Lower bound of 95% CI on model probability
        ci_upper: Upper bound of 95% CI on model probability
        is_calibrated: Whether confidence is backed by backtest data
        calibration_note: Explanation of calibration status
    """
    odds_str = f"+{odds}" if odds > 0 else str(odds)
    tier_label, color = _ev_tier_indicator(ev_pct, prob_edge_positive)
    conf_badge = _confidence_badge(confidence, prob_edge_positive)
    cal_indicator = _calibration_indicator(is_calibrated)

    embed = discord.Embed(
        title=f"⚡ VALUE ALERT — {tier_label}",
        color=color,
    )

    # Game info with visual hierarchy
    embed.add_field(
        name="🏟️ Game",
        value=f"**{game}**",
        inline=True,
    )
    embed.add_field(
        name="🎯 Selection",
        value=f"**{side}** `{odds_str}`",
        inline=True,
    )
    embed.add_field(
        name="📊 Confidence",
        value=f"{conf_badge}\n{cal_indicator}",
        inline=True,
    )

    # Edge metrics block with statistical info
    metrics_text = f"```\nExpected Value:   +{ev_pct:.2f}%\nEdge Size:        {edge:+.1f} pts\n"

    # Add statistical confidence if available
    if prob_edge_positive is not None:
        metrics_text += f"P(Edge > 0):      {prob_edge_positive:.1%}\n"

    metrics_text += "────────────────────────\n"

    # Add confidence interval if available
    if ci_lower is not None and ci_upper is not None:
        metrics_text += f"Model Prob 95% CI: [{ci_lower:.1f}%, {ci_upper:.1f}%]\n"

    metrics_text += (
        f"Model Line:       {model_line:+.1f}\n"
        f"Market Line:      {market_line:+.1f}\n"
        f"Discrepancy:      {abs(model_line - market_line):.1f} pts\n"
        f"```"
    )

    embed.add_field(
        name="📈 Edge Metrics",
        value=metrics_text,
        inline=False,
    )

    # Calibration note
    if calibration_note:
        embed.add_field(
            name="📋 Confidence Note",
            value=f"*{calibration_note}*",
            inline=False,
        )

    # Action guidance
    embed.add_field(
        name="⚠️ Action Notes",
        value=(
            "• Line may move quickly — verify before betting\n"
            "• Check multiple sportsbooks for best price\n"
            "• Size according to Kelly recommendation"
        ),
        inline=False,
    )

    embed.set_footer(text="SharpEdge • Statistical confidence based on model uncertainty")
    embed.timestamp = discord.utils.utcnow()
    return embed


def movement_alert_embed(
    game: str,
    old_line: float,
    new_line: float,
    direction: str,
    interpretation: str = "",
) -> discord.Embed:
    """Build institutional-grade line movement alert embed."""
    movement = new_line - old_line
    movement_abs = abs(movement)

    # Color based on movement significance
    if movement_abs >= 2.0:
        color = 0xFF4444  # Red - significant
        severity = "🔴 MAJOR MOVE"
    elif movement_abs >= 1.0:
        color = 0xFFA500  # Orange - moderate
        severity = "🟠 NOTABLE MOVE"
    else:
        color = 0x7289DA  # Blue - minor
        severity = "🔵 MINOR MOVE"

    # Direction arrow
    arrow = "📈" if movement > 0 else "📉" if movement < 0 else "➡️"

    embed = discord.Embed(
        title=f"📊 LINE MOVEMENT — {severity}",
        color=color,
    )

    embed.add_field(
        name="🏟️ Game",
        value=f"**{game}**",
        inline=False,
    )

    embed.add_field(
        name=f"{arrow} Movement",
        value=(
            f"```\n"
            f"Previous:  {old_line:+.1f}\n"
            f"Current:   {new_line:+.1f}\n"
            f"────────────────────\n"
            f"Change:    {movement:+.1f} pts ({direction})\n"
            f"```"
        ),
        inline=False,
    )

    if interpretation:
        embed.add_field(
            name="💡 Interpretation",
            value=f"*{interpretation}*",
            inline=False,
        )

    embed.set_footer(text="SharpEdge Line Tracker • Monitor for continued movement")
    embed.timestamp = discord.utils.utcnow()
    return embed


def _split_text(text: str, max_length: int) -> list[str]:
    """Split text into chunks respecting Discord field limits."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find a good split point (newline or space)
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    return chunks
