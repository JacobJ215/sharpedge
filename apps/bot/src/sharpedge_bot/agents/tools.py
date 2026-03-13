"""Tool definitions for OpenAI Agents SDK.

These are the tools agents can call to retrieve data and perform calculations.
All tools operate on predefined, safe operations — no raw SQL or arbitrary code.
"""

import json
import logging
from datetime import date, datetime, timezone

from agents import function_tool

logger = logging.getLogger("sharpedge.agents.tools")


@function_tool
def get_current_odds(sport: str, game_query: str) -> str:
    """Get current odds for a game from multiple sportsbooks.

    Args:
        sport: Sport code (NFL, NBA, MLB, NHL)
        game_query: Game to look up (e.g., 'Chiefs Raiders')
    """
    from sharpedge_bot.services.odds_service import get_odds_client
    import os

    api_key = os.environ.get("ODDS_API_KEY", "")
    redis_url = os.environ.get("REDIS_URL", "")
    if not api_key:
        return json.dumps({"error": "Odds API not configured"})

    try:
        from sharpedge_shared.types import Sport as SportEnum
        client = get_odds_client(api_key, redis_url)
        game = client.find_game(game_query, SportEnum(sport) if sport else None)
        if not game:
            return json.dumps({"error": f"Game not found: {game_query}"})

        comparison = client.get_line_comparison(game)
        return json.dumps({
            "home_team": comparison.home_team,
            "away_team": comparison.away_team,
            "commence_time": comparison.commence_time.isoformat(),
            "spreads": [
                {"book": l.sportsbook_display, "line": l.line, "odds": l.odds, "side": l.side}
                for l in comparison.spread_home + comparison.spread_away
            ],
            "totals": [
                {"book": l.sportsbook_display, "line": l.line, "odds": l.odds, "side": l.side}
                for l in comparison.total_over + comparison.total_under
            ],
            "moneylines": [
                {"book": l.sportsbook_display, "odds": l.odds, "side": l.side}
                for l in comparison.moneyline_home + comparison.moneyline_away
            ],
        }, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@function_tool
def calculate_expected_value(model_probability: float, american_odds: int) -> str:
    """Calculate expected value for a bet.

    Args:
        model_probability: Estimated true win probability (0.0 to 1.0)
        american_odds: American odds (e.g., -110, +150)
    """
    from sharpedge_models.ev_calculator import calculate_ev
    result = calculate_ev(model_probability, american_odds)
    return json.dumps(result)


@function_tool
def query_user_performance(user_id: str, period: str = "all") -> str:
    """Query a user's betting performance summary.

    Args:
        user_id: The user's database UUID
        period: Time period - 'today', 'week', 'month', 'season', or 'all'
    """
    from sharpedge_db.queries.bets import get_performance_summary
    from sharpedge_bot.services.stats_service import _resolve_dates

    start, end = _resolve_dates(period)
    summary = get_performance_summary(user_id, start, end)
    return json.dumps({
        "total_bets": summary.total_bets,
        "wins": summary.wins,
        "losses": summary.losses,
        "pushes": summary.pushes,
        "win_rate": float(summary.win_rate),
        "units_won": float(summary.units_won),
        "roi": float(summary.roi),
        "avg_odds": summary.avg_odds,
    })


@function_tool
def query_sport_breakdown(user_id: str, period: str = "all") -> str:
    """Query a user's performance breakdown by sport.

    Args:
        user_id: The user's database UUID
        period: Time period
    """
    from sharpedge_db.queries.bets import get_breakdown_by_sport
    from sharpedge_bot.services.stats_service import _resolve_dates

    start, end = _resolve_dates(period)
    breakdown = get_breakdown_by_sport(user_id, start, end)
    return json.dumps([
        {
            "sport": b.sport,
            "total_bets": b.total_bets,
            "wins": b.wins,
            "losses": b.losses,
            "win_rate": float(b.win_rate),
            "units_won": float(b.units_won),
            "roi": float(b.roi),
        }
        for b in breakdown
    ])


@function_tool
def query_bet_type_breakdown(user_id: str, period: str = "all") -> str:
    """Query a user's performance breakdown by bet type.

    Args:
        user_id: The user's database UUID
        period: Time period
    """
    from sharpedge_db.queries.bets import get_breakdown_by_bet_type
    from sharpedge_bot.services.stats_service import _resolve_dates

    start, end = _resolve_dates(period)
    breakdown = get_breakdown_by_bet_type(user_id, start, end)
    return json.dumps([
        {
            "bet_type": b.bet_type,
            "total_bets": b.total_bets,
            "wins": b.wins,
            "losses": b.losses,
            "win_rate": float(b.win_rate),
            "units_won": float(b.units_won),
            "roi": float(b.roi),
        }
        for b in breakdown
    ])


@function_tool
def query_clv_analysis(user_id: str, period: str = "all") -> str:
    """Query a user's closing line value (CLV) analysis.

    Args:
        user_id: The user's database UUID
        period: Time period
    """
    from sharpedge_db.queries.bets import get_clv_summary
    from sharpedge_bot.services.stats_service import _resolve_dates

    start, end = _resolve_dates(period)
    clv = get_clv_summary(user_id, start, end)
    return json.dumps({
        "avg_clv": float(clv.avg_clv),
        "positive_clv_count": clv.positive_clv_count,
        "negative_clv_count": clv.negative_clv_count,
        "positive_clv_rate": float(clv.positive_clv_rate),
    })


@function_tool
def query_recent_bets(user_id: str, limit: int = 20) -> str:
    """Get a user's most recent bets.

    Args:
        user_id: The user's database UUID
        limit: Max number of bets to return
    """
    from sharpedge_db.queries.bets import get_bet_history
    bets = get_bet_history(user_id, limit=limit)
    return json.dumps([
        {
            "id": b.id[:8],
            "sport": b.sport,
            "selection": b.selection,
            "odds": b.odds,
            "units": float(b.units),
            "result": b.result,
            "profit": float(b.profit) if b.profit else None,
            "clv_points": float(b.clv_points) if b.clv_points else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        }
        for b in bets
    ], default=str)


# ============================================
# NEW ANALYTICS TOOLS
# ============================================


@function_tool
def get_opening_line(game_id: str, bet_type: str = "spread") -> str:
    """Get the opening line for a game.

    Args:
        game_id: Game identifier
        bet_type: 'spread', 'total', or 'moneyline'
    """
    from sharpedge_db.queries.opening_lines import get_opening_line as get_opening
    from sharpedge_db.queries.opening_lines import calculate_movement_from_open

    opening = get_opening(game_id, bet_type)
    if not opening:
        return json.dumps({"error": "Opening line not found"})

    return json.dumps({
        "game_id": game_id,
        "bet_type": bet_type,
        "opening_line": opening.get("line"),
        "opening_odds_a": opening.get("odds_a"),
        "opening_odds_b": opening.get("odds_b"),
        "captured_at": opening.get("captured_at"),
    }, default=str)


@function_tool
def get_line_movement_from_open(game_id: str, current_line: float, bet_type: str = "spread") -> str:
    """Calculate how much a line has moved from its opening.

    Args:
        game_id: Game identifier
        current_line: Current line value
        bet_type: 'spread' or 'total'
    """
    from sharpedge_db.queries.opening_lines import calculate_movement_from_open

    movement = calculate_movement_from_open(game_id, current_line, bet_type)
    if not movement:
        return json.dumps({"error": "Opening line not found"})

    return json.dumps(movement, default=str)


@function_tool
def get_consensus_line(game_id: str) -> str:
    """Get the market consensus line for a game.

    Returns the median line across all sportsbooks and fair (no-vig) probabilities.

    Args:
        game_id: Game identifier
    """
    from sharpedge_db.queries.consensus import get_consensus

    consensus = get_consensus(game_id)
    if not consensus:
        return json.dumps({"error": "Consensus not available"})

    return json.dumps({
        "game_id": game_id,
        "spread_consensus": consensus.get("spread_consensus"),
        "spread_weighted": consensus.get("spread_weighted_consensus"),
        "spread_range": f"{consensus.get('spread_min')} to {consensus.get('spread_max')}",
        "total_consensus": consensus.get("total_consensus"),
        "total_weighted": consensus.get("total_weighted_consensus"),
        "total_range": f"{consensus.get('total_min')} to {consensus.get('total_max')}",
        "fair_probs": {
            "spread_home": consensus.get("spread_fair_home_prob"),
            "spread_away": consensus.get("spread_fair_away_prob"),
            "total_over": consensus.get("total_fair_over_prob"),
            "total_under": consensus.get("total_fair_under_prob"),
            "ml_home": consensus.get("ml_fair_home_prob"),
            "ml_away": consensus.get("ml_fair_away_prob"),
        },
        "market_agreement": consensus.get("market_agreement"),
    }, default=str)


@function_tool
def get_public_betting(game_id: str) -> str:
    """Get public betting percentages and sharp money indicators.

    Args:
        game_id: Game identifier
    """
    from sharpedge_db.queries.public_betting import get_public_betting as get_public

    data = get_public(game_id)
    if not data:
        return json.dumps({"error": "Public betting data not available"})

    return json.dumps({
        "game_id": game_id,
        "spread": {
            "ticket_home": data.get("spread_ticket_home"),
            "ticket_away": data.get("spread_ticket_away"),
            "money_home": data.get("spread_money_home"),
            "money_away": data.get("spread_money_away"),
            "sharp_side": data.get("spread_sharp_side"),
            "divergence": data.get("spread_divergence"),
        },
        "total": {
            "ticket_over": data.get("total_ticket_over"),
            "ticket_under": data.get("total_ticket_under"),
            "money_over": data.get("total_money_over"),
            "money_under": data.get("total_money_under"),
            "sharp_side": data.get("total_sharp_side"),
            "divergence": data.get("total_divergence"),
        },
        "source": data.get("source"),
        "captured_at": data.get("captured_at"),
    }, default=str)


@function_tool
def get_sharp_plays(min_divergence: float = 10, sport: str | None = None) -> str:
    """Find games with sharp money signals.

    Sharp money is indicated when money percentage diverges from ticket percentage.

    Args:
        min_divergence: Minimum money/ticket divergence percentage
        sport: Filter by sport (optional)
    """
    from sharpedge_db.queries.public_betting import get_sharp_plays as get_sharps

    plays = get_sharps(min_divergence=min_divergence, sport=sport)
    return json.dumps(plays[:10], default=str)


@function_tool
def get_line_movements(game_id: str, significant_only: bool = True) -> str:
    """Get line movement history for a game.

    Args:
        game_id: Game identifier
        significant_only: Only return significant movements
    """
    from sharpedge_db.queries.line_movements import get_line_movements as get_movements
    from sharpedge_db.queries.line_movements import get_movement_summary

    movements = get_movements(game_id, significant_only=significant_only)
    summary = get_movement_summary(game_id)

    return json.dumps({
        "summary": summary,
        "movements": movements[:10],
    }, default=str)


@function_tool
def get_steam_moves(hours: int = 24, sport: str | None = None) -> str:
    """Get recent steam moves (sharp money line movements).

    Args:
        hours: Look back this many hours
        sport: Filter by sport (optional)
    """
    from sharpedge_db.queries.line_movements import get_recent_steam_moves

    moves = get_recent_steam_moves(hours=hours, sport=sport)
    return json.dumps(moves[:10], default=str)


@function_tool
def get_active_value_plays(sport: str | None = None, min_ev: float = 2.0) -> str:
    """Get active positive EV betting opportunities.

    Args:
        sport: Filter by sport (optional)
        min_ev: Minimum expected value percentage
    """
    from sharpedge_db.queries.value_plays import get_active_value_plays as get_values

    plays = get_values(sport=sport, min_ev=min_ev)
    return json.dumps([
        {
            "game": p.get("game"),
            "side": p.get("side"),
            "sportsbook": p.get("sportsbook"),
            "odds": p.get("market_odds"),
            "ev_pct": p.get("ev_percentage"),
            "edge_pct": p.get("edge_percentage"),
            "confidence": p.get("confidence"),
        }
        for p in plays[:10]
    ], default=str)


@function_tool
def get_active_arbitrage(min_profit: float = 0.5) -> str:
    """Get active arbitrage opportunities.

    Args:
        min_profit: Minimum profit percentage
    """
    from sharpedge_db.queries.arbitrage import get_active_arbitrage as get_arbs

    arbs = get_arbs(min_profit=min_profit)
    return json.dumps([
        {
            "game": a.get("game"),
            "bet_type": a.get("bet_type"),
            "book_a": a.get("book_a"),
            "side_a": a.get("side_a"),
            "odds_a": a.get("odds_a"),
            "stake_a_pct": a.get("stake_a_percentage"),
            "book_b": a.get("book_b"),
            "side_b": a.get("side_b"),
            "odds_b": a.get("odds_b"),
            "stake_b_pct": a.get("stake_b_percentage"),
            "profit_pct": a.get("profit_percentage"),
        }
        for a in arbs[:5]
    ], default=str)


@function_tool
def calculate_no_vig_odds(odds_a: int, odds_b: int) -> str:
    """Calculate fair (no-vig) odds and probabilities.

    Args:
        odds_a: American odds for side A (e.g., -110)
        odds_b: American odds for side B (e.g., -110)
    """
    from sharpedge_analytics import calculate_fair_odds

    result = calculate_fair_odds(odds_a, odds_b)
    return json.dumps({
        "fair_prob_a": result.fair_prob_a,
        "fair_prob_b": result.fair_prob_b,
        "fair_odds_a": result.fair_odds_a,
        "fair_odds_b": result.fair_odds_b,
        "vig_percentage": result.vig_percentage,
    })


@function_tool
def check_arbitrage(odds_a: int, odds_b: int, book_a: str = "Book A", book_b: str = "Book B") -> str:
    """Check if arbitrage exists between two odds.

    Args:
        odds_a: American odds for side A at book A
        odds_b: American odds for side B at book B
        book_a: Name of first sportsbook
        book_b: Name of second sportsbook
    """
    from sharpedge_analytics import find_arbitrage, calculate_arbitrage_stakes

    arb = find_arbitrage(odds_a, odds_b, book_a, book_b)

    if not arb.exists:
        return json.dumps({
            "exists": False,
            "total_implied": arb.total_implied,
            "message": "No arbitrage opportunity - combined probability >= 100%",
        })

    stakes = calculate_arbitrage_stakes(1000, odds_a, odds_b)

    return json.dumps({
        "exists": True,
        "profit_pct": arb.profit_percentage,
        "stake_a_pct": arb.stake_a_percentage,
        "stake_b_pct": arb.stake_b_percentage,
        "example_1000": {
            "stake_a": stakes["stake_a"],
            "stake_b": stakes["stake_b"],
            "guaranteed_profit": stakes["guaranteed_profit"],
        },
    })


@function_tool
def analyze_key_numbers(line: float, sport: str = "NFL") -> str:
    """Analyze a line's relationship to key numbers.

    Key numbers are common margins of victory (3 and 7 in NFL).

    Args:
        line: The spread line to analyze
        sport: Sport code
    """
    from sharpedge_analytics import analyze_key_numbers as analyze

    analysis = analyze(line, sport)
    return json.dumps({
        "current_line": analysis.current_line,
        "nearest_key": analysis.nearest_key,
        "distance_to_key": analysis.distance_to_key,
        "key_frequency": f"{analysis.key_frequency * 100:.1f}%",
        "crosses_key": analysis.crosses_key,
        "value_adjustment": analysis.value_adjustment,
    })


@function_tool
def get_weather_impact(game_id: str) -> str:
    """Get weather conditions and betting impact for an outdoor game.

    Args:
        game_id: Game identifier
    """
    from sharpedge_db.client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("game_weather")
        .select("*")
        .eq("game_id", game_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return json.dumps({"error": "Weather data not available"})

    weather = result.data[0]

    if weather.get("is_dome"):
        return json.dumps({
            "venue": weather.get("venue"),
            "is_dome": True,
            "impact": "None - indoor venue",
        })

    return json.dumps({
        "venue": weather.get("venue"),
        "temperature": weather.get("temperature"),
        "wind_speed": weather.get("wind_speed"),
        "wind_direction": weather.get("wind_direction"),
        "precipitation_chance": weather.get("precipitation_chance"),
        "conditions": weather.get("conditions"),
        "total_adjustment": weather.get("total_adjustment"),
        "impact_level": weather.get("impact_level"),
    }, default=str)


@function_tool
def get_schedule_edge(game_id: str, team: str) -> str:
    """Get schedule/rest advantage for a team.

    Args:
        game_id: Game identifier
        team: Team name to check
    """
    from sharpedge_db.client import get_supabase_client

    client = get_supabase_client()
    result = (
        client.table("team_schedules")
        .select("*")
        .eq("game_id", game_id)
        .eq("team", team)
        .limit(1)
        .execute()
    )

    if not result.data:
        return json.dumps({"error": "Schedule data not available"})

    schedule = result.data[0]
    return json.dumps({
        "team": team,
        "rest_days": schedule.get("rest_days"),
        "is_back_to_back": schedule.get("is_back_to_back"),
        "is_3_in_4": schedule.get("is_3_in_4"),
        "travel_miles": schedule.get("travel_miles"),
        "timezone_change": schedule.get("timezone_change"),
        "previous_result": schedule.get("previous_result"),
        "schedule_edge": schedule.get("schedule_edge"),
    }, default=str)
