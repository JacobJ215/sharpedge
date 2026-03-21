"""Rest and travel impact analysis.

Schedule-based edges are well-documented in sports betting:
- Rest advantages matter significantly in NBA
- Travel (especially timezone changes) impacts performance
- Back-to-backs, 3-in-4s create predictable patterns
"""

from dataclasses import dataclass
from enum import StrEnum


class ScheduleSpot(StrEnum):
    """Types of schedule situations."""

    NORMAL = "normal"
    BACK_TO_BACK = "back_to_back"  # 2nd of B2B
    THREE_IN_FOUR = "3_in_4"  # 3rd game in 4 nights
    FOUR_IN_FIVE = "4_in_5"  # 4th game in 5 nights
    REST_ADVANTAGE = "rest_advantage"  # Significant rest edge
    TRAVEL_DISADVANTAGE = "travel_disadvantage"  # Long travel
    TRAP_GAME = "trap_game"  # Classic letdown spot
    REVENGE = "revenge"  # Playing team that beat them


@dataclass
class TeamSchedule:
    """Schedule context for a team."""

    team: str
    rest_days: int  # Days since last game
    games_last_7_days: int
    games_last_14_days: int
    is_back_to_back: bool
    is_3_in_4: bool
    is_4_in_5: bool
    travel_miles: int | None  # Miles traveled from last game
    timezone_change: int  # Hours of timezone change
    is_home: bool
    previous_opponent: str | None
    previous_result: str | None  # "W", "L"
    next_opponent: str | None  # For lookahead spot detection


@dataclass
class ScheduleEdge:
    """Calculated schedule-based edge."""

    spread_adjustment: float  # Points to adjust spread
    edge_description: str
    home_schedule: TeamSchedule
    away_schedule: TeamSchedule
    factors: list[str]
    spots_detected: list[ScheduleSpot]
    betting_implications: list[str]


# Historical ATS data for schedule spots (approximate)
SPOT_ATS_DATA = {
    "NBA": {
        "back_to_back_road": -2.0,  # B2B road team adjustment
        "back_to_back_home": -0.5,  # B2B home team less affected
        "rest_advantage_per_day": 0.5,  # Per day of rest advantage
        "timezone_3_plus": -1.5,  # 3+ hour timezone change
        "4_in_5": -2.5,  # 4th game in 5 nights
    },
    "NFL": {
        "short_week_road": -1.0,  # Thursday game, road team
        "bye_week_advantage": 1.5,  # Coming off bye
        "cross_country": -1.0,  # Cross-country travel
    },
    "MLB": {
        "day_after_night": -0.3,  # Day game after night game
        "travel_adjustment": -0.5,  # Travel day before game
    },
    "NHL": {
        "back_to_back": -0.5,  # B2B in hockey
        "3_in_4": -0.75,  # 3 games in 4 nights
    },
}


def calculate_schedule_edge(
    home_schedule: TeamSchedule,
    away_schedule: TeamSchedule,
    sport: str = "NBA",
) -> ScheduleEdge:
    """Calculate schedule-based betting edge.

    Args:
        home_schedule: Home team's schedule context
        away_schedule: Away team's schedule context
        sport: Sport for adjustment factors

    Returns:
        ScheduleEdge with spread adjustment and analysis
    """
    adjustment = 0
    factors = []
    spots = []
    implications = []

    spot_data = SPOT_ATS_DATA.get(sport.upper(), {})

    # Rest advantage calculation
    rest_diff = home_schedule.rest_days - away_schedule.rest_days

    if abs(rest_diff) >= 2:
        if rest_diff > 0:
            rest_adj = min(rest_diff, 3) * spot_data.get("rest_advantage_per_day", 0.5)
            adjustment += rest_adj
            factors.append(f"Home +{rest_diff} rest days: +{rest_adj:.1f} pts")
            spots.append(ScheduleSpot.REST_ADVANTAGE)
        else:
            rest_adj = max(rest_diff, -3) * spot_data.get("rest_advantage_per_day", 0.5)
            adjustment += rest_adj
            factors.append(f"Away +{abs(rest_diff)} rest days: {rest_adj:.1f} pts")

    # Back-to-back analysis
    if away_schedule.is_back_to_back:
        b2b_adj = spot_data.get("back_to_back_road", -1.5)
        adjustment -= b2b_adj  # Negative adjustment helps home team
        factors.append(f"Away on B2B: +{abs(b2b_adj):.1f} pts for home")
        spots.append(ScheduleSpot.BACK_TO_BACK)
        implications.append("Fade the road B2B team")

    if home_schedule.is_back_to_back:
        b2b_adj = spot_data.get("back_to_back_home", -0.5)
        adjustment += b2b_adj
        factors.append(f"Home on B2B: {b2b_adj:.1f} pts")
        spots.append(ScheduleSpot.BACK_TO_BACK)

    # 3-in-4 / 4-in-5 analysis
    if away_schedule.is_4_in_5:
        adj = spot_data.get("4_in_5", -2.0)
        adjustment -= adj
        factors.append(f"Away playing 4th in 5 nights: +{abs(adj):.1f} pts for home")
        spots.append(ScheduleSpot.FOUR_IN_FIVE)
        implications.append("Severe fatigue spot for away team")

    elif away_schedule.is_3_in_4:
        adj = spot_data.get("3_in_4", -1.0)
        adjustment -= adj
        factors.append(f"Away playing 3rd in 4 nights: +{abs(adj):.1f} pts for home")
        spots.append(ScheduleSpot.THREE_IN_FOUR)

    # Travel/timezone analysis
    if away_schedule.timezone_change >= 3:
        tz_adj = spot_data.get("timezone_3_plus", -1.0)
        adjustment -= tz_adj
        factors.append(
            f"Away {away_schedule.timezone_change}hr timezone change: +{abs(tz_adj):.1f} pts for home"
        )
        spots.append(ScheduleSpot.TRAVEL_DISADVANTAGE)
        implications.append("West to East travel is particularly impactful")

    # NFL bye week
    if sport.upper() == "NFL" and home_schedule.rest_days >= 10:  # Coming off bye
        bye_adj = spot_data.get("bye_week_advantage", 1.5)
        adjustment += bye_adj
        factors.append(f"Home off bye week: +{bye_adj:.1f} pts")

    # Determine edge description
    if abs(adjustment) >= 2:
        edge_desc = "Significant schedule edge"
    elif abs(adjustment) >= 1:
        edge_desc = "Moderate schedule edge"
    elif abs(adjustment) >= 0.5:
        edge_desc = "Minor schedule edge"
    else:
        edge_desc = "No significant schedule edge"

    if not factors:
        factors.append("Both teams on normal rest")

    return ScheduleEdge(
        spread_adjustment=round(adjustment, 1),
        edge_description=edge_desc,
        home_schedule=home_schedule,
        away_schedule=away_schedule,
        factors=factors,
        spots_detected=spots,
        betting_implications=implications,
    )


def detect_trap_game(
    team_schedule: TeamSchedule,
    opponent_record: str,  # "12-3" or similar
    next_game_importance: str,  # "rivalry", "playoff", "normal"
) -> tuple[bool, str]:
    """Detect if this is a potential trap game.

    Trap games occur when a good team is expected to overlook
    a weaker opponent, often before a big game.

    Args:
        team_schedule: The favored team's schedule
        opponent_record: Current opponent's record
        next_game_importance: How important is the next game

    Returns:
        (is_trap, explanation)
    """
    # Parse opponent record
    try:
        wins, losses = map(int, opponent_record.replace("-", " ").split())
        opp_win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5
    except (ValueError, ZeroDivisionError):
        opp_win_pct = 0.5

    is_trap = False
    reasons = []

    # Weak opponent
    if opp_win_pct < 0.35:
        reasons.append("facing weak opponent")

    # Big game coming up
    if next_game_importance in ["rivalry", "playoff"]:
        reasons.append(f"big {next_game_importance} game upcoming")

    # Just beat a good team (letdown spot)
    if team_schedule.previous_result == "W" and team_schedule.previous_opponent:
        reasons.append("coming off emotional win")

    is_trap = len(reasons) >= 2

    explanation = f"Trap game alert: {', '.join(reasons)}" if is_trap else ""

    return is_trap, explanation


def detect_revenge_spot(
    team_schedule: TeamSchedule,
    previous_matchup_result: str | None,  # "L 98-105" or similar
    days_since_loss: int | None,
) -> tuple[bool, str]:
    """Detect if this is a revenge game spot.

    Args:
        team_schedule: Team's schedule context
        previous_matchup_result: Result of last meeting
        days_since_loss: How long ago the loss occurred

    Returns:
        (is_revenge, explanation)
    """
    if not previous_matchup_result:
        return False, ""

    if previous_matchup_result.startswith("L"):
        if days_since_loss and days_since_loss < 30:
            return True, f"Revenge spot: Lost to this team {days_since_loss} days ago"
        elif days_since_loss and days_since_loss < 90:
            return True, "Revenge spot: Previous loss still fresh"

    return False, ""


def format_schedule_display(schedule: TeamSchedule) -> str:
    """Format schedule info for display."""
    parts = []

    if schedule.is_back_to_back:
        parts.append("B2B")
    elif schedule.is_3_in_4:
        parts.append("3-in-4")
    elif schedule.is_4_in_5:
        parts.append("4-in-5")

    if schedule.rest_days == 0:
        parts.append("0 days rest")
    elif schedule.rest_days == 1:
        parts.append("1 day rest")
    elif schedule.rest_days >= 7:
        parts.append(f"{schedule.rest_days} days rest (extended)")
    else:
        parts.append(f"{schedule.rest_days} days rest")

    if schedule.timezone_change >= 2:
        parts.append(f"{schedule.timezone_change}hr TZ change")

    return " | ".join(parts) if parts else "Normal schedule"
