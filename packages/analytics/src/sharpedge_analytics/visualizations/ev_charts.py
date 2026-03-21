"""EV distribution and CLV charts."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from sharpedge_analytics.visualizations._helpers import (
    fig_to_png_bytes,
    setup_discord_style,
)

# Discord color constants
DISCORD_DARK_BG = "#36393f"
DISCORD_DARKER_BG = "#2f3136"
DISCORD_DARKEST_BG = "#202225"
DISCORD_TEXT = "#dcddde"
DISCORD_MUTED = "#72767d"
DISCORD_GREEN = "#43b581"
DISCORD_RED = "#f04747"
DISCORD_YELLOW = "#faa61a"
DISCORD_BLUE = "#7289da"
DISCORD_PURPLE = "#9b59b6"


def create_ev_distribution_chart(
    plays: list[dict],
    title: str = "Value Play Distribution",
) -> bytes:
    """Create a chart showing EV distribution of current value plays.

    Args:
        plays: List of dicts with 'ev_percentage', 'confidence', 'side', 'sport'

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    if not plays:
        # Empty state chart
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5,
            0.5,
            "No value plays currently available",
            ha="center",
            va="center",
            fontsize=14,
            color=DISCORD_MUTED,
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        return fig_to_png_bytes(fig)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Left: EV histogram
    evs = [p.get("ev_percentage", 0) for p in plays]

    colors = [
        DISCORD_GREEN if ev >= 3 else DISCORD_YELLOW if ev >= 1.5 else DISCORD_MUTED for ev in evs
    ]

    ax1.barh(range(len(plays)), evs, color=colors, height=0.7)

    # Labels
    for i, (p, ev) in enumerate(zip(plays, evs, strict=False)):
        label = f"{p.get('side', 'Unknown')[:15]}"
        ax1.text(0.1, i, label, va="center", fontsize=9, color=DISCORD_TEXT)
        ax1.text(
            ev + 0.1, i, f"+{ev:.1f}%", va="center", fontsize=9, fontweight="bold", color=colors[i]
        )

    ax1.set_xlabel("Expected Value (%)", fontsize=11)
    ax1.set_title("Value Plays by EV", fontsize=12, fontweight="bold")
    ax1.set_yticks([])
    ax1.axvline(x=0, color=DISCORD_MUTED, linewidth=0.5)
    ax1.set_xlim(-0.5, max(evs) + 1)

    # Right: Confidence distribution
    confidence_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for p in plays:
        conf = p.get("confidence", "LOW")
        if conf in confidence_counts:
            confidence_counts[conf] += 1

    conf_colors = [DISCORD_GREEN, DISCORD_YELLOW, DISCORD_RED]
    _wedges, _texts, _autotexts = ax2.pie(
        confidence_counts.values(),
        labels=confidence_counts.keys(),
        colors=conf_colors,
        autopct=lambda pct: f"{int(pct / 100 * len(plays))}" if pct > 0 else "",
        startangle=90,
        textprops={"color": DISCORD_TEXT, "fontsize": 11},
    )

    ax2.set_title("Confidence Levels", fontsize=12, fontweight="bold")

    plt.suptitle(title, fontsize=14, fontweight="bold", y=1.02)
    plt.tight_layout()
    return fig_to_png_bytes(fig)


def create_clv_chart(
    clv_values: list[float],
    bet_labels: list[str] | None = None,
    rolling_window: int = 10,
) -> bytes:
    """Create a Closing Line Value chart with rolling average.

    Args:
        clv_values: List of CLV percentages for each bet
        bet_labels: Optional labels for each bet
        rolling_window: Window size for rolling average

    Returns:
        PNG bytes ready for Discord upload
    """
    setup_discord_style()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[2, 1])

    x = range(len(clv_values))

    # Individual CLV bars
    colors = [DISCORD_GREEN if clv > 0 else DISCORD_RED for clv in clv_values]
    ax1.bar(x, clv_values, color=colors, alpha=0.7, width=0.8)

    # Rolling average line
    if len(clv_values) >= rolling_window:
        rolling_avg = np.convolve(
            clv_values, np.ones(rolling_window) / rolling_window, mode="valid"
        )
        rolling_x = range(rolling_window - 1, len(clv_values))
        ax1.plot(
            rolling_x,
            rolling_avg,
            color=DISCORD_PURPLE,
            linewidth=2.5,
            label=f"{rolling_window}-bet avg",
            zorder=5,
        )

    # Zero line
    ax1.axhline(y=0, color=DISCORD_MUTED, linewidth=1)

    # Average CLV annotation
    avg_clv = np.mean(clv_values)
    color = DISCORD_GREEN if avg_clv > 0 else DISCORD_RED
    ax1.axhline(
        y=avg_clv, color=color, linestyle="--", linewidth=1.5, label=f"Avg: {avg_clv:+.2f}%"
    )

    ax1.set_ylabel("CLV (%)", fontsize=11)
    ax1.set_title("Closing Line Value by Bet", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3, axis="y")

    # Bottom: CLV distribution histogram
    ax2.hist(clv_values, bins=20, color=DISCORD_BLUE, alpha=0.7, edgecolor=DISCORD_MUTED)
    ax2.axvline(x=0, color=DISCORD_MUTED, linewidth=1)
    ax2.axvline(x=avg_clv, color=color, linewidth=2, linestyle="--")

    ax2.set_xlabel("CLV (%)", fontsize=11)
    ax2.set_ylabel("Count", fontsize=11)
    ax2.set_title("CLV Distribution", fontsize=11)

    plt.tight_layout()
    return fig_to_png_bytes(fig)
