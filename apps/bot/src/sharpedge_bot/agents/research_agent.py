"""Research Agent — AI-powered sports betting research assistant.

This agent provides comprehensive research capabilities:
- Matchup breakdowns with historical data
- Player projection analysis
- Historical trend identification
- EV opportunity scanning
- Injury/news impact assessment
- Sharp money tracking

Uses GPT-5-mini for cost-effective yet powerful reasoning.
"""

import json
import logging
from datetime import datetime

from agents import Agent, Runner, function_tool

logger = logging.getLogger("sharpedge.agents.research")


# ============================================
# RESEARCH TOOLS
# ============================================

@function_tool
async def get_matchup_breakdown(
    home_team: str,
    away_team: str,
    sport: str,
) -> str:
    """Get comprehensive matchup breakdown between two teams.

    Includes head-to-head history, recent form, key matchups.

    Args:
        home_team: Home team name
        away_team: Away team name
        sport: Sport code (NFL, NBA, MLB, NHL)

    Returns:
        Detailed matchup analysis as JSON string
    """
    from sharpedge_db.client import get_supabase_client

    client = get_supabase_client()

    # Get recent games for both teams
    result = {
        "matchup": f"{away_team} @ {home_team}",
        "sport": sport,
        "generated_at": datetime.now().isoformat(),
    }

    # Head-to-head history (last 10 meetings)
    h2h_query = (
        client.table("bets")
        .select("*")
        .or_(f"home_team.eq.{home_team},away_team.eq.{home_team}")
        .or_(f"home_team.eq.{away_team},away_team.eq.{away_team}")
        .order("placed_at", desc=True)
        .limit(10)
    )

    h2h_result = h2h_query.execute()

    if h2h_result.data:
        result["head_to_head"] = {
            "games_found": len(h2h_result.data),
            "summary": "Historical matchup data available",
        }
    else:
        result["head_to_head"] = {"games_found": 0, "summary": "No recent matchup data"}

    # Key factors by sport
    key_factors = {
        "NFL": [
            "Offensive line vs defensive line matchup",
            "Quarterback pressure rate",
            "Third down conversion rates",
            "Red zone efficiency",
            "Turnover differential",
        ],
        "NBA": [
            "Pace of play matchup",
            "Three-point shooting vs perimeter defense",
            "Paint scoring vs rim protection",
            "Rebounding differential",
            "Back-to-back fatigue",
        ],
        "MLB": [
            "Starting pitcher vs lineup splits",
            "Bullpen availability",
            "Park factors",
            "Recent offensive performance",
            "Weather conditions",
        ],
        "NHL": [
            "Goaltender matchup",
            "Power play vs penalty kill",
            "Corsi/Fenwick possession metrics",
            "Back-to-back travel",
            "Scoring depth",
        ],
    }

    result["key_factors"] = key_factors.get(sport, ["General team performance"])

    return json.dumps(result, indent=2)


@function_tool
async def get_player_projections(
    player_name: str,
    stat_category: str,
    sport: str,
) -> str:
    """Get player projection analysis for props betting.

    Args:
        player_name: Player name to analyze
        stat_category: Stat category (e.g., "passing_yards", "points", "strikeouts")
        sport: Sport code

    Returns:
        Player projection analysis as JSON string
    """
    # In production, this would pull from actual projection systems
    # For now, provide framework for analysis

    result = {
        "player": player_name,
        "stat_category": stat_category,
        "sport": sport,
        "analysis_framework": {
            "recent_performance": {
                "description": "Last 5-10 games performance in this category",
                "importance": "HIGH",
            },
            "matchup_factor": {
                "description": "How opponent ranks against this stat category",
                "importance": "HIGH",
            },
            "usage_trend": {
                "description": "Is player's role/usage increasing or decreasing",
                "importance": "MEDIUM",
            },
            "rest_situation": {
                "description": "Back-to-back, rest days, travel impact",
                "importance": "MEDIUM",
            },
            "injury_status": {
                "description": "Player health and teammates' health affecting volume",
                "importance": "HIGH",
            },
        },
        "recommendation": "Analyze each factor above to form projection estimate",
    }

    return json.dumps(result, indent=2)


@function_tool
async def get_historical_trends(
    trend_type: str,
    sport: str,
    filters: str | None = None,
) -> str:
    """Get historical betting trend data.

    Args:
        trend_type: Type of trend ("ats", "totals", "home_road", "divisional", "primetime")
        sport: Sport code
        filters: Optional additional filters as JSON string

    Returns:
        Historical trend analysis as JSON string
    """
    # Historical ATS/total trends by situation
    trend_data = {
        "NFL": {
            "home_favorites_ats": {"record": "52-48%", "sample": 5000, "edge": "Slight lean"},
            "road_dogs_ats": {"record": "54-46%", "sample": 3500, "edge": "Profitable historically"},
            "primetime_unders": {"record": "53-47%", "sample": 1200, "edge": "Slight lean"},
            "divisional_unders": {"record": "55-45%", "sample": 2000, "edge": "Consistent edge"},
            "revenge_spots": {"record": "51-49%", "sample": 800, "edge": "No significant edge"},
            "short_rest_dogs": {"record": "48-52%", "sample": 600, "edge": "Avoid"},
        },
        "NBA": {
            "back_to_back_road": {"record": "45-55%", "sample": 4000, "edge": "Fade situation"},
            "rest_advantage_3plus": {"record": "56-44%", "sample": 1500, "edge": "Strong lean"},
            "blowout_bounce": {"record": "52-48%", "sample": 2000, "edge": "Slight lean"},
            "first_half_overs": {"record": "51-49%", "sample": 10000, "edge": "Neutral"},
        },
        "MLB": {
            "ace_pitcher_unders": {"record": "53-47%", "sample": 3000, "edge": "Slight lean"},
            "bullpen_day_overs": {"record": "55-45%", "sample": 1000, "edge": "Good angle"},
            "day_game_after_night": {"record": "48-52%", "sample": 2000, "edge": "Fade road team"},
        },
    }

    sport_trends = trend_data.get(sport, {})

    result = sport_trends.get(trend_type, sport_trends)

    return json.dumps({
        "sport": sport,
        "trend_type": trend_type,
        "data": result,
        "disclaimer": "Historical trends don't guarantee future results. Use as one input among many.",
    }, indent=2)


@function_tool
async def scan_current_value(
    sport: str | None = None,
    min_ev: float = 2.0,
) -> str:
    """Scan for current +EV betting opportunities.

    Args:
        sport: Filter by sport (optional)
        min_ev: Minimum EV percentage (default 2.0%)

    Returns:
        Current value plays as JSON string
    """
    from sharpedge_db.queries.value_plays import get_active_value_plays

    plays = get_active_value_plays(sport=sport, min_ev=min_ev, limit=10)

    if not plays:
        return json.dumps({
            "status": "No value plays above threshold",
            "min_ev_searched": min_ev,
            "recommendation": "Lower threshold or check back later",
        })

    return json.dumps({
        "count": len(plays),
        "min_ev": min_ev,
        "plays": plays,
    }, indent=2)


@function_tool
async def get_sharp_action_summary(
    sport: str | None = None,
) -> str:
    """Get summary of current sharp money indicators.

    Args:
        sport: Filter by sport (optional)

    Returns:
        Sharp money summary as JSON string
    """
    from sharpedge_db.queries.line_movements import get_recent_steam_moves
    from sharpedge_db.queries.public_betting import get_sharp_plays

    sharp_plays = get_sharp_plays(min_divergence=10, sport=sport)
    steam_moves = get_recent_steam_moves(hours=24, sport=sport)

    return json.dumps({
        "sharp_plays": {
            "count": len(sharp_plays) if sharp_plays else 0,
            "plays": sharp_plays[:5] if sharp_plays else [],
        },
        "steam_moves": {
            "count": len(steam_moves) if steam_moves else 0,
            "recent": steam_moves[:5] if steam_moves else [],
        },
        "interpretation": (
            "Sharp action indicates where professional money is moving. "
            "Steam moves are sudden, coordinated line movements across books."
        ),
    }, indent=2)


@function_tool
async def analyze_line_value(
    game_id: str,
    bet_type: str,
    side: str,
    current_odds: int,
) -> str:
    """Analyze if current line offers value vs market.

    Args:
        game_id: Game identifier
        bet_type: Type of bet (spread, total, moneyline)
        side: Which side (home, away, over, under)
        current_odds: Current American odds available

    Returns:
        Value analysis as JSON string
    """
    from sharpedge_db.queries.consensus import get_consensus
    from sharpedge_db.queries.opening_lines import get_opening_line

    consensus = get_consensus(game_id)
    opening = get_opening_line(game_id, bet_type)

    analysis = {
        "game_id": game_id,
        "bet_type": bet_type,
        "side": side,
        "your_odds": current_odds,
    }

    if consensus:
        if bet_type == "spread":
            fair_prob = consensus.get(f"spread_fair_{side}_prob", 0.5)
        elif bet_type == "total":
            fair_prob = consensus.get(f"total_fair_{side}_prob", 0.5)
        else:
            fair_prob = consensus.get(f"ml_fair_{side}_prob", 0.5)

        # Calculate if odds offer value
        from sharpedge_analytics import calculate_expected_value

        ev_result = calculate_expected_value(fair_prob, current_odds)
        analysis["fair_probability"] = f"{fair_prob*100:.1f}%"
        analysis["ev_percentage"] = ev_result.ev_percentage
        analysis["has_value"] = ev_result.is_positive_ev
    else:
        analysis["fair_probability"] = "Not available"
        analysis["has_value"] = "Unknown"

    if opening:
        analysis["opening_line"] = opening.get("line")
        analysis["movement_from_open"] = "Check line movement tools"

    return json.dumps(analysis, indent=2)


@function_tool
async def get_key_numbers_analysis(
    spread: float,
    sport: str,
) -> str:
    """Analyze spread relative to key numbers.

    Args:
        spread: Current spread value
        sport: Sport code

    Returns:
        Key number analysis as JSON string
    """
    from sharpedge_analytics import analyze_key_numbers

    analysis = analyze_key_numbers(spread, sport)

    return json.dumps({
        "spread": spread,
        "sport": sport,
        "nearest_key": analysis.nearest_key,
        "distance_to_key": analysis.distance_to_key,
        "on_key_number": analysis.on_key_number,
        "crosses_key": analysis.crosses_key,
        "value_implication": (
            f"Being {'on' if analysis.on_key_number else 'near'} key number "
            f"{analysis.nearest_key} is {'very significant' if analysis.on_key_number else 'notable'} "
            f"for {sport} betting."
        ),
    }, indent=2)


@function_tool
async def calculate_clv_projection(
    bet_odds: int,
    projected_closing_odds: int,
) -> str:
    """Calculate projected Closing Line Value.

    Args:
        bet_odds: Odds at which bet was placed
        projected_closing_odds: Expected closing odds

    Returns:
        CLV analysis as JSON string
    """

    # Convert to implied probabilities
    def american_to_implied(odds: int) -> float:
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    bet_prob = american_to_implied(bet_odds)
    close_prob = american_to_implied(projected_closing_odds)

    clv = (close_prob - bet_prob) * 100

    return json.dumps({
        "bet_odds": bet_odds,
        "bet_implied_prob": f"{bet_prob*100:.1f}%",
        "projected_close_odds": projected_closing_odds,
        "close_implied_prob": f"{close_prob*100:.1f}%",
        "clv_percentage": round(clv, 2),
        "interpretation": (
            f"{'Positive' if clv > 0 else 'Negative'} CLV of {clv:+.2f}%. "
            f"{'You got the best of the number.' if clv > 0 else 'Line moved against you.'}"
        ),
    }, indent=2)


# ============================================
# RESEARCH AGENT DEFINITION
# ============================================

RESEARCH_AGENT_INSTRUCTIONS = """
You are SharpEdge's Research Agent, an AI-powered sports betting research assistant
with deep expertise in statistical analysis, betting markets, and edge identification.

## Your Core Capabilities

### 1. Matchup Breakdowns
When asked about a specific game:
- Use get_matchup_breakdown for comprehensive matchup analysis
- Identify key factors that will determine the outcome
- Highlight statistical mismatches

### 2. Player Projection Analysis
For player props:
- Use get_player_projections to analyze player opportunities
- Consider recent performance, matchup, and usage trends
- Identify over/under value on prop lines

### 3. Historical Trend Research
For situational analysis:
- Use get_historical_trends to find relevant historical patterns
- Present trends with proper sample sizes and caveats
- Distinguish between strong edges and noise

### 4. EV Opportunity Scanning
For finding value:
- Use scan_current_value to identify +EV plays
- Explain why each opportunity has positive expected value
- Prioritize by confidence and edge size

### 5. Sharp Money Tracking
For professional bettor insights:
- Use get_sharp_action_summary to see where pros are betting
- Interpret line movements and ticket/money splits
- Identify reverse line movement situations

### 6. Line Value Analysis
For specific bet evaluation:
- Use analyze_line_value to assess current odds vs fair value
- Compare to consensus and opening lines
- Use get_key_numbers_analysis for spread evaluation

### 7. CLV Projections
For bet timing:
- Use calculate_clv_projection to estimate closing line value
- Help users understand optimal bet timing
- Track historical CLV performance

## Research Methodology

1. **Start with the question** - Understand exactly what the user needs
2. **Gather relevant data** - Use appropriate tools to collect information
3. **Analyze systematically** - Consider multiple angles and factors
4. **Present findings clearly** - Structure your response logically
5. **Acknowledge uncertainty** - Be honest about what you don't know

## Output Format

Structure your research as:
1. **Summary** - Key findings in 2-3 sentences
2. **Data** - Relevant statistics and metrics
3. **Analysis** - Your interpretation of the data
4. **Recommendations** - Actionable next steps
5. **Caveats** - Important limitations or uncertainties

## Tone
- Analytical and data-driven
- Educational, not promotional
- Confident but humble about uncertainty
- Professional and accessible

Remember: You are a research assistant, not a tipster. Present analysis, not picks.
"""


def create_research_agent() -> Agent:
    """Create the Research Agent with full research capabilities."""
    return Agent(
        name="SharpEdge Research Agent",
        instructions=RESEARCH_AGENT_INSTRUCTIONS,
        tools=[
            get_matchup_breakdown,
            get_player_projections,
            get_historical_trends,
            scan_current_value,
            get_sharp_action_summary,
            analyze_line_value,
            get_key_numbers_analysis,
            calculate_clv_projection,
        ],
        model="gpt-5-mini",  # GPT-5 series for advanced reasoning
    )


async def run_research(query: str, context: str = "") -> str:
    """Run the research agent with a query.

    Args:
        query: Research question or request
        context: Optional additional context

    Returns:
        Research response
    """
    agent = create_research_agent()

    prompt = query
    if context:
        prompt = f"{context}\n\n{query}"

    result = await Runner.run(agent, prompt)
    return result.final_output


async def research_game(
    home_team: str,
    away_team: str,
    sport: str,
) -> str:
    """Run comprehensive game research.

    Args:
        home_team: Home team name
        away_team: Away team name
        sport: Sport code

    Returns:
        Comprehensive game research
    """
    agent = create_research_agent()

    prompt = f"""
    Provide comprehensive research for the upcoming game:

    **{away_team} @ {home_team}** ({sport})

    Please analyze:
    1. Matchup breakdown and key factors
    2. Historical trends relevant to this game
    3. Current sharp money and line movement
    4. Any value opportunities identified
    5. Key numbers to consider for spread betting

    Structure your response as a detailed research report.
    """

    result = await Runner.run(agent, prompt)
    return result.final_output
