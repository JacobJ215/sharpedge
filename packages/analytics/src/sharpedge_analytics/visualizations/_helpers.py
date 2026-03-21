"""Shared helpers used across all visualization sub-modules."""

import base64
import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

# Discord-optimized professional dark theme constants
DISCORD_DARK_BG = "#36393f"
DISCORD_DARKER_BG = "#2f3136"
DISCORD_DARKEST_BG = "#202225"
DISCORD_TEXT = "#dcddde"
DISCORD_TEXT_SECONDARY = "#8e9297"
DISCORD_MUTED = "#72767d"
DISCORD_GREEN = "#43b581"
DISCORD_GREEN_BRIGHT = "#00ff7f"
DISCORD_RED = "#f04747"
DISCORD_RED_BRIGHT = "#ff4444"
DISCORD_YELLOW = "#faa61a"
DISCORD_BLUE = "#7289da"
DISCORD_PURPLE = "#9b59b6"
DISCORD_CYAN = "#00d4ff"


def setup_discord_style() -> None:
    """Configure matplotlib for institutional-grade Discord charts."""
    plt.style.use("dark_background")
    plt.rcParams.update(
        {
            "figure.facecolor": DISCORD_DARK_BG,
            "axes.facecolor": DISCORD_DARKER_BG,
            "axes.edgecolor": DISCORD_MUTED,
            "axes.labelcolor": DISCORD_TEXT,
            "axes.labelsize": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "text.color": DISCORD_TEXT,
            "xtick.color": DISCORD_TEXT,
            "ytick.color": DISCORD_TEXT,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "grid.color": DISCORD_MUTED,
            "grid.alpha": 0.2,
            "grid.linestyle": "--",
            "legend.facecolor": DISCORD_DARKEST_BG,
            "legend.edgecolor": DISCORD_MUTED,
            "legend.fontsize": 9,
            "legend.framealpha": 0.9,
            "font.family": "sans-serif",
            "font.size": 10,
            "figure.dpi": 150,
        }
    )


def fig_to_png_bytes(fig: plt.Figure, dpi: int = 200) -> bytes:
    """Convert matplotlib figure to high-quality PNG bytes for Discord upload."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        pad_inches=0.15,
    )
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64 string."""
    png_bytes = fig_to_png_bytes(fig)
    return base64.b64encode(png_bytes).decode("utf-8")


def add_watermark(ax: plt.Axes, text: str = "SharpEdge", alpha: float = 0.1) -> None:
    """Add subtle watermark to chart for branding."""
    ax.text(
        0.98,
        0.02,
        text,
        transform=ax.transAxes,
        fontsize=14,
        color=DISCORD_TEXT,
        alpha=alpha,
        ha="right",
        va="bottom",
        fontweight="bold",
        style="italic",
    )


def add_gradient_fill(ax: plt.Axes, x: list, y: list, color: str, alpha: float = 0.3) -> None:
    """Add gradient fill under a line for professional effect."""
    ax.fill_between(
        x,
        y,
        0,
        alpha=alpha,
        color=color,
        linewidth=0,
    )
    # Add subtle gradient effect with layered fills
    for i in range(3):
        ax.fill_between(
            x,
            y,
            0,
            alpha=alpha * (0.3 - i * 0.08),
            color=color,
            linewidth=0,
        )
