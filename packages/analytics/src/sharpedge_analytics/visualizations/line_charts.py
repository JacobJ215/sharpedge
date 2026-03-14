"""Line movement, bankroll, odds comparison, and arbitrage charts.

These charts share line/bar chart patterns and the helpers:
setup_discord_style, add_watermark, add_gradient_fill.
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.gridspec import GridSpec
from datetime import datetime

# Discord-optimized professional dark theme constants
DISCORD_DARK_BG = '#36393f'
DISCORD_DARKER_BG = '#2f3136'
DISCORD_DARKEST_BG = '#202225'
DISCORD_TEXT = '#dcddde'
DISCORD_TEXT_SECONDARY = '#8e9297'
DISCORD_MUTED = '#72767d'
DISCORD_GREEN = '#43b581'
DISCORD_GREEN_BRIGHT = '#00ff7f'
DISCORD_RED = '#f04747'
DISCORD_RED_BRIGHT = '#ff4444'
DISCORD_YELLOW = '#faa61a'
DISCORD_BLUE = '#7289da'
DISCORD_PURPLE = '#9b59b6'
DISCORD_CYAN = '#00d4ff'

from sharpedge_analytics.visualizations._helpers import (
    setup_discord_style, add_watermark, add_gradient_fill, fig_to_png_bytes,
)


def create_line_movement_chart(
    timestamps: list[datetime],
    lines: list[float],
    team_name: str,
    opening_line: float | None = None,
    consensus_line: float | None = None,
    key_numbers: list[float] | None = None,
    show_velocity: bool = True,
) -> bytes:
    """Create institutional-grade line movement chart.

    Features:
    - Gradient fill under movement line
    - Key number zones with annotations
    - Movement velocity indicator
    - Professional annotations and legend

    Args:
        timestamps: List of datetime objects for each line snapshot
        lines: Spread values at each timestamp
        team_name: Team name for title
        opening_line: Optional opening line to mark
        consensus_line: Optional consensus line to mark
        key_numbers: Optional key numbers to highlight (e.g., 3, 7 for NFL)
        show_velocity: Show movement speed indicator

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    # Create figure with optional velocity subplot
    if show_velocity and len(lines) >= 3:
        fig = plt.figure(figsize=(11, 7))
        gs = GridSpec(3, 1, height_ratios=[3, 1, 0.3], hspace=0.15)
        ax = fig.add_subplot(gs[0])
        ax_vel = fig.add_subplot(gs[1], sharex=ax)
    else:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        ax_vel = None

    # Key numbers shading (before main line for layering)
    if key_numbers:
        for i, kn in enumerate(key_numbers):
            intensity = 0.12 - (i * 0.02)  # Fade intensity for secondary key numbers
            ax.axhspan(
                kn - 0.25, kn + 0.25,
                alpha=intensity,
                color=DISCORD_YELLOW,
                linewidth=0,
            )
            ax.text(
                timestamps[0], kn,
                f' KEY {abs(kn):.0f}',
                fontsize=8,
                color=DISCORD_YELLOW,
                alpha=0.7,
                va='center',
                fontweight='bold',
            )

    # Main line plot with gradient fill
    line_color = DISCORD_CYAN
    ax.plot(
        timestamps, lines,
        color=line_color,
        linewidth=2.5,
        marker='o',
        markersize=5,
        markerfacecolor=DISCORD_DARKER_BG,
        markeredgecolor=line_color,
        markeredgewidth=2,
        label='Current Line',
        zorder=5,
    )

    # Gradient fill under line
    add_gradient_fill(ax, timestamps, lines, line_color, alpha=0.2)

    # Opening line reference with annotation
    if opening_line is not None:
        ax.axhline(
            y=opening_line,
            color=DISCORD_MUTED,
            linestyle='--',
            linewidth=1.5,
            alpha=0.8,
        )
        ax.annotate(
            f'OPEN {opening_line:+.1f}',
            xy=(timestamps[0], opening_line),
            xytext=(-5, 0),
            textcoords='offset points',
            fontsize=9,
            color=DISCORD_MUTED,
            ha='right',
            va='center',
            fontweight='bold',
        )

    # Consensus line reference
    if consensus_line is not None:
        ax.axhline(
            y=consensus_line,
            color=DISCORD_PURPLE,
            linestyle=':',
            linewidth=2,
            alpha=0.8,
        )
        ax.annotate(
            f'CONSENSUS {consensus_line:+.1f}',
            xy=(timestamps[-1], consensus_line),
            xytext=(5, 0),
            textcoords='offset points',
            fontsize=9,
            color=DISCORD_PURPLE,
            ha='left',
            va='center',
            fontweight='bold',
        )

    # Movement summary box
    if len(lines) >= 2:
        movement = lines[-1] - lines[0]
        color = DISCORD_GREEN_BRIGHT if movement > 0 else DISCORD_RED_BRIGHT if movement < 0 else DISCORD_MUTED
        direction = "▲" if movement > 0 else "▼" if movement < 0 else "●"

        # Add highlighted endpoint
        ax.scatter(
            [timestamps[-1]], [lines[-1]],
            s=150,
            color=color,
            zorder=10,
            edgecolors=DISCORD_TEXT,
            linewidths=2,
        )

        # Movement annotation with background box
        ax.annotate(
            f'{direction} {abs(movement):.1f} pts',
            xy=(timestamps[-1], lines[-1]),
            xytext=(15, 15 if movement >= 0 else -15),
            textcoords='offset points',
            fontsize=12,
            fontweight='bold',
            color=color,
            bbox=dict(
                boxstyle='round,pad=0.4',
                facecolor=DISCORD_DARKEST_BG,
                edgecolor=color,
                alpha=0.9,
            ),
            arrowprops=dict(
                arrowstyle='->',
                color=color,
                connectionstyle='arc3,rad=0.2',
            ),
        )

    # Velocity subplot
    if ax_vel is not None and len(lines) >= 3:
        velocities = np.diff(lines) / np.array([
            max((timestamps[i+1] - timestamps[i]).total_seconds() / 3600, 0.1)
            for i in range(len(timestamps) - 1)
        ])
        vel_times = timestamps[1:]

        colors = [DISCORD_GREEN if v > 0 else DISCORD_RED for v in velocities]
        ax_vel.bar(vel_times, velocities, color=colors, alpha=0.7, width=0.02)
        ax_vel.axhline(y=0, color=DISCORD_MUTED, linewidth=0.5)
        ax_vel.set_ylabel('Velocity\n(pts/hr)', fontsize=9)
        ax_vel.tick_params(labelbottom=False)
        ax_vel.set_ylim(-max(abs(velocities)) * 1.2, max(abs(velocities)) * 1.2)

    ax.set_ylabel('Spread', fontsize=11)
    ax.set_title(
        f'LINE MOVEMENT — {team_name}',
        fontsize=14,
        fontweight='bold',
        pad=15,
    )

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    ax.grid(True, alpha=0.2, linestyle='--')
    ax.invert_yaxis()

    # Add watermark
    add_watermark(ax)

    plt.tight_layout()
    return fig_to_png_bytes(fig)


def create_bankroll_chart(
    dates: list[datetime],
    bankroll_values: list[float],
    bets: list[dict] | None = None,
    show_drawdown: bool = True,
) -> bytes:
    """Create institutional-grade bankroll performance chart.

    Features:
    - Gradient fill with dynamic coloring
    - Win/loss markers with size proportional to profit
    - Drawdown visualization
    - High-water mark tracking
    - Professional ROI annotations

    Args:
        dates: Datetime for each data point
        bankroll_values: Bankroll value at each date
        bets: Optional list of bets with 'date', 'profit', 'result'
        show_drawdown: Show drawdown subplot

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    if show_drawdown and len(bankroll_values) >= 5:
        fig = plt.figure(figsize=(11, 7))
        gs = GridSpec(3, 1, height_ratios=[3, 1, 0.3], hspace=0.12)
        ax = fig.add_subplot(gs[0])
        ax_dd = fig.add_subplot(gs[1], sharex=ax)
    else:
        fig, ax = plt.subplots(figsize=(11, 5.5))
        ax_dd = None

    # Determine if profitable overall
    is_profitable = bankroll_values[-1] >= bankroll_values[0] if bankroll_values else True
    main_color = DISCORD_GREEN if is_profitable else DISCORD_RED

    # Calculate high-water mark
    high_water = np.maximum.accumulate(bankroll_values)

    # High-water mark line
    ax.plot(
        dates, high_water,
        color=DISCORD_CYAN,
        linewidth=1,
        linestyle=':',
        alpha=0.5,
        label='High Water Mark',
    )

    # Main bankroll line
    ax.plot(
        dates, bankroll_values,
        color=main_color,
        linewidth=3,
        label='Bankroll',
        zorder=5,
    )

    # Gradient fill - color based on above/below starting
    starting = bankroll_values[0] if bankroll_values else 0
    for i in range(len(dates) - 1):
        segment_color = DISCORD_GREEN if bankroll_values[i+1] >= starting else DISCORD_RED
        ax.fill_between(
            dates[i:i+2],
            bankroll_values[i:i+2],
            starting,
            alpha=0.15,
            color=segment_color,
            linewidth=0,
        )

    # Starting bankroll reference
    ax.axhline(
        y=starting,
        color=DISCORD_MUTED,
        linestyle='--',
        linewidth=1.5,
        alpha=0.7,
    )
    ax.annotate(
        f'START ${starting:,.0f}',
        xy=(dates[0], starting),
        xytext=(5, -15),
        textcoords='offset points',
        fontsize=9,
        color=DISCORD_MUTED,
        fontweight='bold',
    )

    # Win/loss markers with size proportional to profit
    if bets:
        wins = [(b['date'], b['profit']) for b in bets if b.get('profit', 0) > 0 and b.get('date')]
        losses = [(b['date'], b['profit']) for b in bets if b.get('profit', 0) < 0 and b.get('date')]

        if wins:
            win_dates, win_profits = zip(*wins)
            win_sizes = [min(abs(p) * 5 + 50, 200) for p in win_profits]
            # Find bankroll values at bet times
            win_values = []
            for d in win_dates:
                idx = min(range(len(dates)), key=lambda i: abs(dates[i] - d))
                win_values.append(bankroll_values[idx])
            ax.scatter(
                win_dates, win_values,
                s=win_sizes,
                color=DISCORD_GREEN_BRIGHT,
                marker='^',
                edgecolors=DISCORD_TEXT,
                linewidths=1,
                alpha=0.8,
                zorder=10,
                label='Wins',
            )

        if losses:
            loss_dates, loss_profits = zip(*losses)
            loss_sizes = [min(abs(p) * 5 + 50, 200) for p in loss_profits]
            loss_values = []
            for d in loss_dates:
                idx = min(range(len(dates)), key=lambda i: abs(dates[i] - d))
                loss_values.append(bankroll_values[idx])
            ax.scatter(
                loss_dates, loss_values,
                s=loss_sizes,
                color=DISCORD_RED_BRIGHT,
                marker='v',
                edgecolors=DISCORD_TEXT,
                linewidths=1,
                alpha=0.8,
                zorder=10,
                label='Losses',
            )

    # ROI annotation box
    if len(bankroll_values) >= 2:
        roi = ((bankroll_values[-1] / bankroll_values[0]) - 1) * 100
        profit = bankroll_values[-1] - bankroll_values[0]
        color = DISCORD_GREEN_BRIGHT if roi >= 0 else DISCORD_RED_BRIGHT

        # Highlight final point
        ax.scatter(
            [dates[-1]], [bankroll_values[-1]],
            s=200,
            color=color,
            zorder=15,
            edgecolors=DISCORD_TEXT,
            linewidths=2,
        )

        # Summary box
        summary_text = f'ROI: {roi:+.1f}%\nP/L: ${profit:+,.0f}'
        ax.annotate(
            summary_text,
            xy=(dates[-1], bankroll_values[-1]),
            xytext=(15, 20 if roi >= 0 else -40),
            textcoords='offset points',
            fontsize=11,
            fontweight='bold',
            color=DISCORD_TEXT,
            bbox=dict(
                boxstyle='round,pad=0.5',
                facecolor=DISCORD_DARKEST_BG,
                edgecolor=color,
                linewidth=2,
                alpha=0.95,
            ),
            arrowprops=dict(
                arrowstyle='->',
                color=color,
                connectionstyle='arc3,rad=0.2',
            ),
        )

    # Drawdown subplot
    if ax_dd is not None:
        drawdown = (np.array(bankroll_values) - high_water) / high_water * 100
        ax_dd.fill_between(dates, drawdown, 0, color=DISCORD_RED, alpha=0.4)
        ax_dd.plot(dates, drawdown, color=DISCORD_RED, linewidth=1.5)
        ax_dd.set_ylabel('Drawdown\n(%)', fontsize=9)
        ax_dd.set_ylim(min(drawdown) * 1.2, 5)
        ax_dd.axhline(y=0, color=DISCORD_MUTED, linewidth=0.5)
        ax_dd.tick_params(labelbottom=False)

        # Max drawdown annotation
        max_dd = min(drawdown)
        max_dd_idx = np.argmin(drawdown)
        ax_dd.annotate(
            f'Max DD: {max_dd:.1f}%',
            xy=(dates[max_dd_idx], max_dd),
            xytext=(5, -10),
            textcoords='offset points',
            fontsize=8,
            color=DISCORD_RED,
            fontweight='bold',
        )

    ax.set_ylabel('Bankroll ($)', fontsize=11)
    ax.set_title('BANKROLL PERFORMANCE', fontsize=14, fontweight='bold', pad=15)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    ax.legend(loc='upper left', framealpha=0.9)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Add watermark
    add_watermark(ax)

    plt.tight_layout()
    return fig_to_png_bytes(fig)


def create_odds_comparison_chart(
    sportsbooks: list[str],
    home_odds: list[int],
    away_odds: list[int],
    home_team: str,
    away_team: str,
    best_home_idx: int | None = None,
    best_away_idx: int | None = None,
) -> bytes:
    """Create a visual odds comparison across sportsbooks.

    Args:
        sportsbooks: List of sportsbook names
        home_odds: Home team American odds at each book
        away_odds: Away team American odds at each book
        home_team: Home team name
        away_team: Away team name
        best_home_idx: Index of best home odds
        best_away_idx: Index of best away odds

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(sportsbooks))
    width = 0.35

    # Home odds bars
    home_colors = [DISCORD_GREEN if i == best_home_idx else DISCORD_BLUE
                   for i in range(len(home_odds))]
    bars1 = ax.bar(x - width/2, home_odds, width, label=home_team,
                   color=home_colors, alpha=0.8)

    # Away odds bars
    away_colors = [DISCORD_GREEN if i == best_away_idx else DISCORD_PURPLE
                   for i in range(len(away_odds))]
    bars2 = ax.bar(x + width/2, away_odds, width, label=away_team,
                   color=away_colors, alpha=0.8)

    # Value labels on bars
    for bar, odds in zip(bars1, home_odds):
        height = bar.get_height()
        label = f'+{odds}' if odds > 0 else str(odds)
        ax.annotate(label, xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    for bar, odds in zip(bars2, away_odds):
        height = bar.get_height()
        label = f'+{odds}' if odds > 0 else str(odds)
        ax.annotate(label, xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0, 3), textcoords='offset points',
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    ax.set_xlabel('Sportsbook', fontsize=11)
    ax.set_ylabel('American Odds', fontsize=11)
    ax.set_title(f'Odds Comparison: {away_team} @ {home_team}',
                 fontsize=14, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(sportsbooks, rotation=45, ha='right')
    ax.legend()

    # Reference line at -110
    ax.axhline(y=-110, color=DISCORD_MUTED, linestyle=':', linewidth=1, alpha=0.5)

    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    return fig_to_png_bytes(fig)


def create_arbitrage_chart(
    arbs: list[dict],
    title: str = "Arbitrage Opportunities",
) -> bytes:
    """Create a visual representation of arbitrage opportunities.

    Args:
        arbs: List of arb dicts with 'profit_pct', 'book_a', 'book_b', 'game'

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    if not arbs:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, 'No arbitrage opportunities available',
                ha='center', va='center', fontsize=14, color=DISCORD_MUTED)
        ax.axis('off')
        return fig_to_png_bytes(fig)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Sort by profit
    arbs_sorted = sorted(arbs, key=lambda x: x.get('profit_pct', 0), reverse=True)[:10]

    y_pos = range(len(arbs_sorted))
    profits = [a.get('profit_pct', 0) for a in arbs_sorted]

    # Color gradient based on profit
    colors = [DISCORD_GREEN if p >= 1.5 else DISCORD_YELLOW if p >= 0.75 else DISCORD_MUTED
              for p in profits]

    bars = ax.barh(y_pos, profits, color=colors, height=0.6)

    # Labels
    labels = [f"{a.get('book_a', '?')[:8]} - {a.get('book_b', '?')[:8]}"
              for a in arbs_sorted]
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)

    # Profit annotations
    for bar, profit in zip(bars, profits):
        width = bar.get_width()
        ax.annotate(f'+{profit:.2f}%',
                    xy=(width, bar.get_y() + bar.get_height()/2),
                    xytext=(5, 0), textcoords='offset points',
                    va='center', fontsize=10, fontweight='bold',
                    color=DISCORD_GREEN)

    ax.set_xlabel('Guaranteed Profit (%)', fontsize=11)
    ax.set_title(f'{title}', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    return fig_to_png_bytes(fig)
