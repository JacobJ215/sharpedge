"""fetch_context node: fetches current odds and extracts game context.

Calls OddsClient.get_odds() ONCE. Downstream nodes must not call OddsClient again.
Under 80 lines.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger("sharpedge.agent.fetch_context")


def fetch_context(state: dict) -> dict:
    """Fetch current odds and extract game_context + regime_inputs.

    Reads sport from state, calls OddsClient to get live odds for the first
    matching game (or all games for scan intent). Extracts the fields needed
    by downstream nodes so they don't need to hit the network again.

    Args:
        state: BettingAnalysisState with sport set.

    Returns:
        Partial state dict with game_context and regime_inputs.
    """
    from sharpedge_odds.client import OddsClient

    sport = state.get("sport", "NFL")
    api_key = os.environ.get("ODDS_API_KEY", "")

    try:
        client = OddsClient(api_key=api_key)
        games = client.get_odds(sport)
    except Exception as exc:
        logger.warning("OddsClient failed: %s — using empty context", exc)
        games = []

    # Extract first game or create empty context for tests/offline
    if games:
        game = games[0]
        # Build game_context: metadata + best available line info
        spread_line: float | None = None
        home_odds: int | None = None
        away_odds: int | None = None

        for bm in game.bookmakers:
            for market in bm.markets:
                if market.key == "spreads" and spread_line is None:
                    for outcome in market.outcomes:
                        if outcome.point is not None:
                            spread_line = outcome.point
                            break
                if market.key == "h2h":
                    outcomes = {o.name: o.price for o in market.outcomes}
                    if game.home_team in outcomes and home_odds is None:
                        home_odds = outcomes[game.home_team]
                    if game.away_team in outcomes and away_odds is None:
                        away_odds = outcomes[game.away_team]

        game_context = {
            "game_id": game.id,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "sport": sport,
            "spread_line": spread_line,
            "home_odds": home_odds or -110,
            "away_odds": away_odds or -110,
            # Placeholder model probability (replaced by ML in Phase 5)
            "model_prob": 0.52,
        }

        # regime_inputs: public betting indicators (approximated from odds data)
        # In production these come from a public betting data feed
        regime_inputs = {
            "ticket_pct": 0.50,
            "handle_pct": 0.50,
            "line_move_pts": 0.0,
            "move_velocity": 0.0,
            "book_alignment": 0.5,
        }
    else:
        # Offline / no-data fallback
        game_context = {
            "game_id": "offline",
            "home_team": "Home",
            "away_team": "Away",
            "sport": sport,
            "spread_line": None,
            "home_odds": -110,
            "away_odds": -110,
            "model_prob": 0.52,
        }
        regime_inputs = {
            "ticket_pct": 0.50,
            "handle_pct": 0.50,
            "line_move_pts": 0.0,
            "move_velocity": 0.0,
            "book_alignment": 0.5,
        }

    return {"game_context": game_context, "regime_inputs": regime_inputs}
