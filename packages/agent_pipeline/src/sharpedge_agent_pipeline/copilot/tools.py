"""Copilot tools — 10 @tool functions wrapping the service layer.

Each tool:
- Wraps a package-level service function (no direct Supabase calls here)
- Returns a dict (JSON-serializable) with at most 10 records to limit token usage
- Handles exceptions by returning {"error": str(e)}

Import boundary: packages/* only. Do NOT import from apps/bot (circular dep).
"""

import os
from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

# --- Database service imports ---
from sharpedge_db.queries.bets import get_pending_bets, get_performance_summary
from sharpedge_db.queries.value_plays import get_active_value_plays
from sharpedge_db.queries.line_movements import get_line_movements, get_movement_summary
from sharpedge_db.queries.projections import get_projection

# --- Models and analytics imports ---
from sharpedge_models.monte_carlo import simulate_bankroll

from sharpedge_agent_pipeline.copilot.venue_tools import VENUE_TOOLS


# ---------------------------------------------------------------------------
# Tool 1: get_active_bets
# ---------------------------------------------------------------------------

@tool
def get_active_bets(user_id: str = "", config: RunnableConfig = None) -> dict:
    """Get the user's currently active (pending) bets.

    Returns the 10 most recent pending bets as a JSON-serializable dict.
    Call this when the user asks what bets they have open or active.

    Args:
        user_id: The user's ID. Defaults to empty string (no filter).
        config: LangChain RunnableConfig injected by the graph; carries user_id in configurable.
    """
    # Prefer user_id from graph configurable state (threaded from auth token)
    if config is not None:
        configurable_uid = (config or {}).get("configurable", {}).get("user_id")
        if configurable_uid:
            user_id = configurable_uid
    try:
        bets = get_pending_bets(user_id or "")
        records = []
        for b in bets[:10]:
            records.append({
                "game": str(getattr(b, "game", "") or ""),
                "selection": str(getattr(b, "selection", "") or ""),
                "stake": float(getattr(b, "stake", 0) or 0),
                "odds": int(getattr(b, "odds", 0) or 0),
                "sport": str(getattr(b, "sport", "") or ""),
            })
        return {"bets": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e), "bets": [], "count": 0}


# ---------------------------------------------------------------------------
# Tool 2: get_portfolio_stats
# ---------------------------------------------------------------------------

@tool
def get_portfolio_stats(user_id: str = "", config: RunnableConfig = None) -> dict:
    """Get portfolio performance statistics: win rate, ROI, and total bets.

    Returns an aggregated summary of the user's betting performance.

    Args:
        user_id: The user's ID.
        config: LangChain RunnableConfig injected by the graph; carries user_id in configurable.
    """
    # Prefer user_id from graph configurable state (threaded from auth token)
    if config is not None:
        configurable_uid = (config or {}).get("configurable", {}).get("user_id")
        if configurable_uid:
            user_id = configurable_uid
    try:
        summary = get_performance_summary(user_id or "")
        return {
            "total_bets": int(getattr(summary, "total_bets", 0) or 0),
            "wins": int(getattr(summary, "wins", 0) or 0),
            "losses": int(getattr(summary, "losses", 0) or 0),
            "win_rate": float(getattr(summary, "win_rate", 0) or 0),
            "roi": float(getattr(summary, "roi", 0) or 0),
            "units_won": float(getattr(summary, "units_won", 0) or 0),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 3: analyze_game
# ---------------------------------------------------------------------------

@tool
def analyze_game(game_query: str = "", sport: str = "NBA", user_id: str = "") -> dict:
    """Run a full betting analysis on a specific game.

    Invokes the 9-node analysis graph and returns the analysis report.
    Use this for deep analysis of a specific matchup.

    Args:
        game_query: Game description (e.g., 'Lakers vs Celtics').
        sport: Sport code (e.g., 'NBA', 'NFL').
        user_id: The requesting user's ID.
    """
    try:
        # Import lazily to avoid circular dependency at module load
        from sharpedge_agent_pipeline.graph import ANALYSIS_GRAPH  # type: ignore
        import asyncio

        state = {
            "game_query": game_query,
            "sport": sport,
            "user_id": user_id,
        }
        # Run async graph in sync context
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                ANALYSIS_GRAPH.ainvoke(state, config={"recursion_limit": 25})
            )
        finally:
            loop.close()

        report = result.get("report", "Analysis complete — no report generated.")
        return {"report": str(report)[:2000]}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 4: search_value_plays
# ---------------------------------------------------------------------------

@tool
def search_value_plays(sport: str = "", min_alpha: float = 0.0) -> dict:
    """Search for current value plays (edges) in the market.

    Returns the top 5 value plays sorted by alpha score.

    Args:
        sport: Filter by sport (e.g., 'NBA', 'NFL'). Empty string for all sports.
        min_alpha: Minimum alpha score threshold (0.0 = no filter).
    """
    try:
        plays = get_active_value_plays(sport=sport or None, min_ev=min_alpha or None)
        records = []
        for p in plays[:5]:
            records.append({
                "game": p.get("game"),
                "side": p.get("side"),
                "sport": p.get("sport"),
                "odds": p.get("market_odds"),
                "ev_percentage": p.get("ev_percentage"),
                "confidence": p.get("confidence"),
            })
        return {"value_plays": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e), "value_plays": [], "count": 0}


# ---------------------------------------------------------------------------
# Tool 5: check_line_movement
# ---------------------------------------------------------------------------

@tool
def check_line_movement(game_id: str) -> dict:
    """Check line movement history for a specific game.

    Returns the last 10 line movements, showing direction and magnitude.

    Args:
        game_id: The game identifier.
    """
    try:
        movements = get_line_movements(game_id)
        records = [
            {
                "bet_type": m.get("bet_type"),
                "old_line": m.get("old_line"),
                "new_line": m.get("new_line"),
                "direction": m.get("direction"),
                "movement_type": m.get("movement_type"),
                "is_significant": m.get("is_significant"),
                "detected_at": str(m.get("detected_at") or ""),
            }
            for m in movements[:10]
        ]
        return {"game_id": game_id, "movements": records, "count": len(records)}
    except Exception as e:
        return {"error": str(e), "game_id": game_id, "movements": []}


# ---------------------------------------------------------------------------
# Tool 6: get_sharp_indicators
# ---------------------------------------------------------------------------

@tool
def get_sharp_indicators(game_id: str) -> dict:
    """Get sharp money indicators for a game: steam moves, RLM signals.

    Returns a summary of sharp betting activity including steam counts and
    reverse line movement (RLM) signals.

    Args:
        game_id: The game identifier.
    """
    try:
        summary = get_movement_summary(game_id)
        movements = get_line_movements(game_id, significant_only=True)
        sharp_signals = [
            {
                "bet_type": m.get("bet_type"),
                "movement_type": m.get("movement_type"),
                "interpretation": m.get("interpretation"),
                "magnitude": m.get("magnitude"),
            }
            for m in movements[:5]
            if m.get("movement_type") in ("steam", "rlm")
        ]
        return {
            "game_id": game_id,
            "steam_moves": summary.get("steam_moves", 0),
            "rlm_moves": summary.get("rlm_moves", 0),
            "significant_movements": summary.get("significant_movements", 0),
            "sharp_signals": sharp_signals,
        }
    except Exception as e:
        return {"error": str(e), "game_id": game_id}


# ---------------------------------------------------------------------------
# Tool 7: estimate_bankroll_risk
# ---------------------------------------------------------------------------

@tool
def estimate_bankroll_risk(
    stake: float = 100.0,
    odds: int = -110,
    win_prob: float = 0.52,
    user_id: str = "",
) -> dict:
    """Estimate bankroll ruin probability for a proposed bet using Monte Carlo simulation.

    Simulates 2000 bankroll paths to estimate ruin probability and median outcome.

    Args:
        stake: Dollar amount to wager.
        odds: American odds for the bet (e.g., -110 or +150).
        win_prob: Estimated win probability (0.0 to 1.0).
        user_id: User ID (optional, for future bankroll lookup).
    """
    try:
        # Convert American odds to decimal payout fraction
        if odds > 0:
            win_pct = float(odds) / 100.0
        else:
            win_pct = 100.0 / float(abs(odds))
        loss_pct = 1.0  # lose 100% of the staked fraction

        result = simulate_bankroll(
            win_prob=float(win_prob),
            win_pct=float(win_pct),
            loss_pct=float(loss_pct),
            initial_bankroll=1000.0,
            n_paths=2000,
            n_bets=500,
        )
        return {
            "ruin_probability": round(result.ruin_probability, 4),
            "p50_bankroll": round(result.p50_bankroll, 2),
            "p05_bankroll": round(result.p05_bankroll, 2),
            "p95_bankroll": round(result.p95_bankroll, 2),
            "max_drawdown_p50": round(result.max_drawdown_p50, 4),
            "stake": stake,
            "odds": odds,
            "win_prob": win_prob,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Tool 8: get_prediction_market_edge
# ---------------------------------------------------------------------------

@tool
def get_prediction_market_edge(market_id: str) -> dict:
    """Get current edge analysis for a prediction market.

    Args:
        market_id: Kalshi ticker (e.g. 'FED-25-JUN-T3.5') or Polymarket condition_id

    Returns dict with edge data or {"error": str} if not found.
    """
    import asyncio
    import os
    from sharpedge_analytics.pm_edge_scanner import scan_pm_edges

    async def _fetch_edge() -> dict:
        from sharpedge_feeds.kalshi_client import get_kalshi_client
        from sharpedge_feeds.polymarket_client import get_polymarket_client

        # Try Kalshi first
        kalshi_key = os.environ.get("KALSHI_API_KEY", "")
        kalshi_private_key = os.environ.get("KALSHI_PRIVATE_KEY", "") or None
        if kalshi_key:
            try:
                client = await get_kalshi_client(kalshi_key, private_key_pem=kalshi_private_key)
                market = await client.get_market(market_id)
                await client.close()
                if market:
                    edges = scan_pm_edges([market], [], {}, volume_floor=0.0)
                    if edges:
                        e = edges[0]
                        return {
                            "platform": e.platform,
                            "market_id": e.market_id,
                            "market_title": e.market_title,
                            "market_prob": e.market_prob,
                            "model_prob": e.model_prob,
                            "edge_pct": e.edge_pct,
                            "alpha_score": e.alpha_score,
                            "alpha_badge": e.alpha_badge,
                            "regime": e.regime,
                        }
            except Exception:
                pass

        # Try Polymarket
        try:
            poly_key = os.environ.get("POLYMARKET_API_KEY", None)
            client = await get_polymarket_client(poly_key)
            market = await client.get_market(market_id)
            await client.close()
            if market:
                edges = scan_pm_edges([], [market], {}, volume_floor=0.0)
                if edges:
                    e = edges[0]
                    return {
                        "platform": e.platform,
                        "market_id": e.market_id,
                        "market_title": e.market_title,
                        "market_prob": e.market_prob,
                        "model_prob": e.model_prob,
                        "edge_pct": e.edge_pct,
                        "alpha_score": e.alpha_score,
                        "alpha_badge": e.alpha_badge,
                        "regime": e.regime,
                    }
        except Exception:
            pass

        return {"error": f"Market '{market_id}' not found on Kalshi or Polymarket"}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _fetch_edge())
                return future.result(timeout=10)
        else:
            return loop.run_until_complete(_fetch_edge())
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Tool 9: compare_books
# ---------------------------------------------------------------------------

@tool
def compare_books(game_id: str) -> dict:
    """Compare odds across sportsbooks for a game to identify the best line.

    Requires ODDS_API_KEY environment variable. Returns an offline note if unavailable.

    Args:
        game_id: The game identifier.
    """
    try:
        api_key = os.environ.get("ODDS_API_KEY", "")
        if not api_key:
            return {
                "game_id": game_id,
                "note": "ODDS_API_KEY not set — book comparison unavailable offline.",
                "books": [],
            }

        from sharpedge_odds.client import OddsClient  # type: ignore
        client = OddsClient(api_key=api_key)
        # OddsClient doesn't expose a per-game comparison; return structured note
        return {
            "game_id": game_id,
            "note": "Use sport-level odds endpoint for full book comparison.",
            "books": [],
        }
    except Exception as e:
        return {"error": str(e), "game_id": game_id, "books": []}


# ---------------------------------------------------------------------------
# Tool 10: get_model_predictions
# ---------------------------------------------------------------------------

@tool
def get_model_predictions(game_id: str, sport: str = "NBA") -> dict:
    """Get cached model predictions for a game.

    Returns projected spread, total, and confidence from the model pipeline.

    Args:
        game_id: The game identifier.
        sport: Sport code.
    """
    try:
        projection = get_projection(game_id)
        if projection is None:
            return {
                "game_id": game_id,
                "sport": sport,
                "note": "No model projection found for this game.",
            }
        return {
            "game_id": game_id,
            "sport": str(getattr(projection, "sport", sport) or sport),
            "home_team": str(getattr(projection, "home_team", "") or ""),
            "away_team": str(getattr(projection, "away_team", "") or ""),
            "projected_spread": float(getattr(projection, "projected_spread", 0) or 0),
            "projected_total": float(getattr(projection, "projected_total", 0) or 0),
            "spread_confidence": float(getattr(projection, "spread_confidence", 0) or 0),
            "total_confidence": float(getattr(projection, "total_confidence", 0) or 0),
        }
    except Exception as e:
        return {"error": str(e), "game_id": game_id}


# ---------------------------------------------------------------------------
# Exported tool list
# ---------------------------------------------------------------------------

COPILOT_TOOLS = [
    get_active_bets,
    get_portfolio_stats,
    analyze_game,
    search_value_plays,
    check_line_movement,
    get_sharp_indicators,
    estimate_bankroll_risk,
    get_prediction_market_edge,
    compare_books,
    get_model_predictions,
] + VENUE_TOOLS
