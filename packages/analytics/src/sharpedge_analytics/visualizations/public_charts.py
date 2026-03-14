"""Public betting / sharp money charts."""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np

from sharpedge_analytics.visualizations._helpers import (
    setup_discord_style, fig_to_png_bytes,
)

# Discord color constants
DISCORD_TEXT = '#dcddde'
DISCORD_MUTED = '#72767d'
DISCORD_GREEN = '#43b581'
DISCORD_RED = '#f04747'
DISCORD_BLUE = '#7289da'
DISCORD_PURPLE = '#9b59b6'


def create_public_betting_chart(
    team_names: list[str],
    ticket_pcts: list[float],
    money_pcts: list[float],
    title: str = "Public vs Sharp Money",
) -> bytes:
    """Create a public betting breakdown chart.

    Args:
        team_names: Names of teams/sides
        ticket_pcts: Percentage of tickets on each side
        money_pcts: Percentage of money on each side

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    fig, ax = plt.subplots(figsize=(10, 5))

    x = np.arange(len(team_names))
    width = 0.35

    bars1 = ax.bar(x - width/2, ticket_pcts, width, label='Tickets %',
                   color=DISCORD_BLUE, alpha=0.8)
    bars2 = ax.bar(x + width/2, money_pcts, width, label='Money %',
                   color=DISCORD_PURPLE, alpha=0.8)

    # Divergence annotations
    for i, (tick, money) in enumerate(zip(ticket_pcts, money_pcts)):
        divergence = money - tick
        if abs(divergence) >= 10:
            color = DISCORD_GREEN if divergence > 0 else DISCORD_RED
            symbol = "sharp" if divergence > 0 else "public"
            ax.annotate(f'[{symbol}] {divergence:+.0f}%',
                        xy=(i, max(tick, money) + 2),
                        ha='center', fontsize=10, fontweight='bold', color=color)

    ax.set_xlabel('Side', fontsize=11)
    ax.set_ylabel('Percentage', fontsize=11)
    ax.set_title(f'{title}', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(team_names)
    ax.legend()
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3, axis='y')

    # 50% reference line
    ax.axhline(y=50, color=DISCORD_MUTED, linestyle='--', linewidth=1, alpha=0.5)

    plt.tight_layout()
    return fig_to_png_bytes(fig)
