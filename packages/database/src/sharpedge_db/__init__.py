"""SharpEdge Database Package."""

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import Alert, Bet, OddsHistory, Projection, Usage, User

# Query modules
from sharpedge_db.queries import (
    alerts,
    arbitrage,
    bets,
    consensus,
    injuries,
    line_movements,
    odds_history,
    opening_lines,
    projections,
    public_betting,
    usage,
    users,
    value_plays,
)

__all__ = [
    # Models
    "Alert",
    "Bet",
    "OddsHistory",
    "Projection",
    "Usage",
    "User",
    "alerts",
    "arbitrage",
    "bets",
    "consensus",
    "injuries",
    # Client
    "get_supabase_client",
    "line_movements",
    "odds_history",
    "opening_lines",
    "projections",
    "public_betting",
    "usage",
    # Query modules
    "users",
    "value_plays",
]
