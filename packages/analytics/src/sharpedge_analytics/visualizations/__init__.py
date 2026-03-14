"""Visualizations sub-package for SharpEdge Analytics.

Backward-compatible re-exports of all 9 public functions.
Existing imports like:
    from sharpedge_analytics.visualizations import create_line_movement_chart
continue to work unchanged.
"""

from sharpedge_analytics.visualizations._helpers import (
    fig_to_png_bytes,
    fig_to_base64,
    setup_discord_style,
    add_watermark,
    add_gradient_fill,
)
from sharpedge_analytics.visualizations.line_charts import (
    create_line_movement_chart,
    create_bankroll_chart,
    create_odds_comparison_chart,
    create_arbitrage_chart,
)
from sharpedge_analytics.visualizations.ev_charts import (
    create_ev_distribution_chart,
    create_clv_chart,
)
from sharpedge_analytics.visualizations.public_charts import (
    create_public_betting_chart,
)

__all__ = [
    "create_line_movement_chart",
    "create_ev_distribution_chart",
    "create_bankroll_chart",
    "create_clv_chart",
    "create_odds_comparison_chart",
    "create_arbitrage_chart",
    "create_public_betting_chart",
    "fig_to_png_bytes",
    "fig_to_base64",
    # Internal helpers re-exported for direct use
    "setup_discord_style",
    "add_watermark",
    "add_gradient_fill",
]
