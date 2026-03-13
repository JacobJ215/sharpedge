"""SharpEdge Database Package."""

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import Alert, Bet, OddsHistory, Projection, Usage, User

# Query modules
from sharpedge_db.queries import users, bets, usage, alerts, projections, odds_history
from sharpedge_db.queries import opening_lines, consensus, value_plays, public_betting
from sharpedge_db.queries import line_movements, arbitrage

__all__ = [
    # Models
    "Alert",
    "Bet",
    "OddsHistory",
    "Projection",
    "Usage",
    "User",
    # Client
    "get_supabase_client",
    # Query modules
    "users",
    "bets",
    "usage",
    "alerts",
    "projections",
    "odds_history",
    "opening_lines",
    "consensus",
    "value_plays",
    "public_betting",
    "line_movements",
    "arbitrage",
]
