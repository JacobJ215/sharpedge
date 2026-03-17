"""Extended copilot tools — Tools 11-13.

Kept in a separate file to keep tools.py under 500 lines.
Follows the same patterns as tools.py: @tool, dict return, graceful error handling.
"""

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from sharpedge_db.queries.bets import get_pending_bets


# ---------------------------------------------------------------------------
# Tool 11: compute_kelly
# ---------------------------------------------------------------------------

@tool
def compute_kelly(
    odds: int = -110,
    win_prob: float = 0.55,
    bankroll: float = 1000.0,
    kelly_fraction: float = 0.25,
) -> dict:
    """Compute Kelly Criterion stake size for a bet.

    Calculates the mathematically optimal bet size given your edge.
    Returns full Kelly, fractional Kelly (recommended), and edge percentage.
    All arithmetic is deterministic — no LLM estimation.

    Args:
        odds: American odds (e.g., -110, +150)
        win_prob: Estimated win probability (0.0 to 1.0)
        bankroll: Total bankroll in dollars
        kelly_fraction: Kelly multiplier (0.25 = quarter Kelly, recommended for risk management)
    """
    try:
        # Validate inputs
        if not (0 < win_prob < 1):
            return {"error": "win_prob must be between 0 and 1 (exclusive)."}
        if bankroll <= 0:
            return {"error": "bankroll must be greater than 0."}

        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = odds / 100.0 + 1.0
        else:
            decimal_odds = 100.0 / abs(odds) + 1.0

        b = decimal_odds - 1.0  # net profit per $1 wagered
        q = 1.0 - win_prob

        kelly_full = (b * win_prob - q) / b

        if kelly_full <= 0:
            return {
                "kelly_full_fraction": round(kelly_full, 6),
                "edge_pct": round((win_prob - _implied_prob(odds)) * 100, 4),
                "stake_full_kelly": 0.0,
                "stake_recommended": 0.0,
                "kelly_multiplier": kelly_fraction,
                "decimal_odds": round(decimal_odds, 4),
                "implied_prob": round(_implied_prob(odds), 6),
                "recommendation": "No edge — do not bet.",
                "odds": odds,
                "win_prob": win_prob,
                "bankroll": bankroll,
            }

        stake_full = kelly_full * bankroll
        stake_recommended = kelly_fraction * stake_full
        implied_prob = _implied_prob(odds)
        edge_pct = (win_prob - implied_prob) * 100

        recommendation = (
            f"Bet ${stake_recommended:.2f} ({kelly_fraction * 100:.0f}% Kelly). "
            f"Edge: {edge_pct:.2f}%. Full Kelly would be ${stake_full:.2f}."
        )

        return {
            "kelly_full_fraction": round(kelly_full, 6),
            "edge_pct": round(edge_pct, 4),
            "stake_full_kelly": round(stake_full, 2),
            "stake_recommended": round(stake_recommended, 2),
            "kelly_multiplier": kelly_fraction,
            "decimal_odds": round(decimal_odds, 4),
            "implied_prob": round(implied_prob, 6),
            "recommendation": recommendation,
            "odds": odds,
            "win_prob": win_prob,
            "bankroll": bankroll,
        }
    except Exception as e:
        return {"error": str(e)}


def _implied_prob(odds: int) -> float:
    """Convert American odds to implied probability (vig-inclusive)."""
    if odds < 0:
        return abs(odds) / (abs(odds) + 100.0)
    return 100.0 / (odds + 100.0)


# ---------------------------------------------------------------------------
# Tool 12: get_user_exposure
# ---------------------------------------------------------------------------

@tool
def get_user_exposure(user_id: str = "", config: RunnableConfig = None) -> dict:
    """Get the user's current open bet exposure: total at-risk dollars and breakdown by sport.

    Call this when the user asks 'how much do I have at risk?' or 'what's my exposure?'

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
        bets = get_pending_bets(user_id or "")

        total_at_risk = 0.0
        by_sport: dict = {}
        largest_single_bet = 0.0

        for b in bets:
            stake = float(getattr(b, "stake", 0) or 0)
            sport = str(getattr(b, "sport", "Unknown") or "Unknown")

            total_at_risk += stake
            by_sport[sport] = round(by_sport.get(sport, 0.0) + stake, 2)
            if stake > largest_single_bet:
                largest_single_bet = stake

        return {
            "total_at_risk": round(total_at_risk, 2),
            "open_bet_count": len(bets),
            "by_sport": by_sport,
            "largest_single_bet": round(largest_single_bet, 2),
        }
    except Exception as e:
        return {"error": str(e), "total_at_risk": 0.0, "open_bet_count": 0, "by_sport": {}}


# ---------------------------------------------------------------------------
# Tool 13: get_injury_report
# ---------------------------------------------------------------------------

_ESPN_SPORT_PATHS = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAF": "football/college-football",
    "NCAAB": "basketball/mens-college-basketball",
}

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"


@tool
def get_injury_report(team: str, sport: str = "NBA") -> dict:
    """Get injury report for a team to inform betting decisions.

    Fetches current injury status from ESPN public API. No API key required.
    Call this when the user asks about injuries or player availability.

    Args:
        team: Team name or abbreviation (e.g., 'Lakers', 'LAL', 'Chiefs', 'KC')
        sport: Sport code (NBA, NFL, MLB, NHL, NCAAF, NCAAB)
    """
    try:
        import httpx

        sport_upper = sport.upper()
        sport_path = _ESPN_SPORT_PATHS.get(sport_upper)
        if not sport_path:
            return {
                "error": f"Unsupported sport '{sport}'. Supported: {list(_ESPN_SPORT_PATHS)}",
                "injuries": [],
            }

        with httpx.Client(timeout=10) as client:
            # Step 1: Find the ESPN team_id by searching the teams list
            teams_url = f"{_ESPN_BASE}/{sport_path}/teams"
            teams_resp = client.get(teams_url)
            teams_resp.raise_for_status()
            teams_data = teams_resp.json()

            team_id = _find_team_id(teams_data, team)
            if team_id is None:
                return {
                    "error": f"Team '{team}' not found in ESPN {sport_upper} teams list.",
                    "injuries": [],
                    "note": "Try a different spelling or abbreviation.",
                }

            team_display = _find_team_display(teams_data, team_id)

            # Step 2: Fetch injuries for the found team
            injuries_url = f"{_ESPN_BASE}/{sport_path}/teams/{team_id}/injuries"
            inj_resp = client.get(injuries_url)
            inj_resp.raise_for_status()
            inj_data = inj_resp.json()

        injuries_raw = inj_data.get("injuries", [])
        injuries = []
        for entry in injuries_raw[:8]:
            athlete = entry.get("athlete", {})
            details = entry.get("details", {})
            injuries.append({
                "player": athlete.get("displayName", "Unknown"),
                "status": entry.get("status", "Unknown"),
                "injury_type": details.get("type") or entry.get("type", "Unknown"),
                "note": entry.get("shortComment") or entry.get("longComment") or "",
            })

        return {
            "team": team_display or team,
            "sport": sport_upper,
            "injuries": injuries,
            "count": len(injuries),
        }
    except Exception as e:
        return {
            "error": str(e),
            "injuries": [],
            "note": "ESPN data unavailable.",
        }


def _find_team_id(teams_data: dict, query: str) -> str | None:
    """Search ESPN teams response for a matching team, return ESPN team id."""
    query_lower = query.lower().strip()
    sports_list = teams_data.get("sports", [])
    for sport_entry in sports_list:
        for league in sport_entry.get("leagues", []):
            for team_entry in league.get("teams", []):
                team_obj = team_entry.get("team", {})
                if (
                    query_lower == (team_obj.get("abbreviation") or "").lower()
                    or query_lower in (team_obj.get("displayName") or "").lower()
                    or query_lower in (team_obj.get("shortDisplayName") or "").lower()
                    or query_lower in (team_obj.get("location") or "").lower()
                    or query_lower in (team_obj.get("name") or "").lower()
                ):
                    return str(team_obj.get("id", ""))
    return None


def _find_team_display(teams_data: dict, team_id: str) -> str | None:
    """Return the display name for a given ESPN team id."""
    sports_list = teams_data.get("sports", [])
    for sport_entry in sports_list:
        for league in sport_entry.get("leagues", []):
            for team_entry in league.get("teams", []):
                team_obj = team_entry.get("team", {})
                if str(team_obj.get("id", "")) == team_id:
                    return team_obj.get("displayName")
    return None


# ---------------------------------------------------------------------------
# Exported list of extended tools
# ---------------------------------------------------------------------------

EXTENDED_TOOLS = [
    compute_kelly,
    get_user_exposure,
    get_injury_report,
]
