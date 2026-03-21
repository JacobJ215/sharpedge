"""Visualizations sub-package for SharpEdge Analytics.

Backward-compatible re-exports of all 9 public functions.
Existing imports like:
    from sharpedge_analytics.visualizations import create_line_movement_chart
continue to work unchanged.
"""

from sharpedge_analytics.visualizations._helpers import (
    add_gradient_fill,
    add_watermark,
    fig_to_base64,
    fig_to_png_bytes,
    setup_discord_style,
)
from sharpedge_analytics.visualizations.ev_charts import (
    create_clv_chart,
    create_ev_distribution_chart,
)
from sharpedge_analytics.visualizations.line_charts import (
    create_arbitrage_chart,
    create_bankroll_chart,
    create_line_movement_chart,
    create_odds_comparison_chart,
)
from sharpedge_analytics.visualizations.public_charts import (
    create_public_betting_chart,
)

__all__ = [
    "add_gradient_fill",
    "add_watermark",
    "create_arbitrage_chart",
    "create_bankroll_chart",
    "create_clv_chart",
    "create_ev_distribution_chart",
    "create_line_movement_chart",
    "create_odds_comparison_chart",
    "create_public_betting_chart",
    "fig_to_base64",
    "fig_to_png_bytes",
    # Internal helpers re-exported for direct use
    "setup_discord_style",
]
