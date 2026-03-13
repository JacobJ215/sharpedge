from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import (
    Bet,
    BetTypeBreakdown,
    CLVSummary,
    PerformanceSummary,
    SportBreakdown,
)
from sharpedge_shared.types import BetResult, BetType, Sport


def create_bet(
    user_id: str,
    sport: Sport,
    game: str,
    bet_type: BetType,
    selection: str,
    odds: int,
    units: Decimal,
    stake: Decimal,
    potential_win: Decimal,
    sportsbook: str | None = None,
    notes: str | None = None,
    game_date: date | None = None,
    league: str | None = None,
    opening_line: Decimal | None = None,
    line_at_bet: Decimal | None = None,
) -> Bet:
    """Create a new bet record."""
    client = get_supabase_client()
    data: dict = {
        "user_id": user_id,
        "sport": sport,
        "game": game,
        "bet_type": bet_type,
        "selection": selection,
        "odds": odds,
        "units": float(units),
        "stake": float(stake),
        "potential_win": float(potential_win),
        "result": BetResult.PENDING,
    }
    if league:
        data["league"] = league
    if sportsbook:
        data["sportsbook"] = sportsbook
    if notes:
        data["notes"] = notes
    if game_date:
        data["game_date"] = game_date.isoformat()
    if opening_line is not None:
        data["opening_line"] = float(opening_line)
    if line_at_bet is not None:
        data["line_at_bet"] = float(line_at_bet)

    result = client.table("bets").insert(data).execute()
    return Bet(**result.data[0])


def update_bet_result(
    bet_id: str,
    result: BetResult,
    profit: Decimal,
    closing_line: Decimal | None = None,
    clv_points: Decimal | None = None,
) -> Bet:
    """Record the result of a bet."""
    client = get_supabase_client()
    data: dict = {
        "result": result,
        "profit": float(profit),
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }
    if closing_line is not None:
        data["closing_line"] = float(closing_line)
    if clv_points is not None:
        data["clv_points"] = float(clv_points)

    resp = client.table("bets").update(data).eq("id", bet_id).execute()
    return Bet(**resp.data[0])


def get_bet_by_id(bet_id: str) -> Bet | None:
    """Get a single bet by ID."""
    client = get_supabase_client()
    result = client.table("bets").select("*").eq("id", bet_id).execute()
    if result.data:
        return Bet(**result.data[0])
    return None


def get_pending_bets(user_id: str) -> list[Bet]:
    """Get all pending bets for a user."""
    client = get_supabase_client()
    result = (
        client.table("bets")
        .select("*")
        .eq("user_id", user_id)
        .eq("result", BetResult.PENDING)
        .order("created_at", desc=True)
        .execute()
    )
    return [Bet(**row) for row in result.data]


def get_bet_history(
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    sport: Sport | None = None,
    bet_type: BetType | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Bet]:
    """Get bet history with optional filters."""
    client = get_supabase_client()
    query = client.table("bets").select("*").eq("user_id", user_id)

    if sport:
        query = query.eq("sport", sport)
    if bet_type:
        query = query.eq("bet_type", bet_type)
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return [Bet(**row) for row in result.data]


def _get_date_range(period: str = "all") -> tuple[date, date]:
    """Get start/end dates for a period."""
    today = datetime.now(timezone.utc).date()
    if period == "today":
        return today, today
    if period == "week":
        return today - timedelta(days=7), today
    if period == "month":
        return today - timedelta(days=30), today
    if period == "season":
        # Approximate season start (September 1)
        year = today.year if today.month >= 9 else today.year - 1
        return date(year, 9, 1), today
    # "all" - use a very early date
    return date(2020, 1, 1), today


def get_performance_summary(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PerformanceSummary:
    """Calculate overall performance stats."""
    client = get_supabase_client()
    query = (
        client.table("bets")
        .select("*")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
    )
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    if not bets:
        return PerformanceSummary()

    wins = sum(1 for b in bets if b.result == BetResult.WIN)
    losses = sum(1 for b in bets if b.result == BetResult.LOSS)
    pushes = sum(1 for b in bets if b.result == BetResult.PUSH)
    decided = wins + losses

    total_profit = sum(b.profit or Decimal("0") for b in bets)
    total_stake = sum(b.stake for b in bets)
    total_units_staked = sum(b.units for b in bets)
    avg_unit_size = total_stake / total_units_staked if total_units_staked else Decimal("1")
    units_won = total_profit / avg_unit_size if avg_unit_size else Decimal("0")

    roi = (total_profit / total_stake * 100) if total_stake else Decimal("0")
    win_rate = Decimal(str(wins / decided * 100)) if decided else Decimal("0")
    avg_odds = int(sum(b.odds for b in bets) / len(bets)) if bets else 0

    return PerformanceSummary(
        total_bets=len(bets),
        wins=wins,
        losses=losses,
        pushes=pushes,
        win_rate=win_rate.quantize(Decimal("0.01")),
        units_won=units_won.quantize(Decimal("0.01")),
        roi=roi.quantize(Decimal("0.01")),
        avg_odds=avg_odds,
    )


def get_breakdown_by_sport(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[SportBreakdown]:
    """Get performance breakdown by sport."""
    client = get_supabase_client()
    query = (
        client.table("bets")
        .select("*")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
    )
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    sports: dict[str, list[Bet]] = {}
    for bet in bets:
        sports.setdefault(bet.sport, []).append(bet)

    breakdowns = []
    for sport, sport_bets in sports.items():
        wins = sum(1 for b in sport_bets if b.result == BetResult.WIN)
        losses = sum(1 for b in sport_bets if b.result == BetResult.LOSS)
        decided = wins + losses
        total_profit = sum(b.profit or Decimal("0") for b in sport_bets)
        total_stake = sum(b.stake for b in sport_bets)
        total_units = sum(b.units for b in sport_bets)
        avg_unit = total_stake / total_units if total_units else Decimal("1")
        units_won = total_profit / avg_unit if avg_unit else Decimal("0")
        roi = (total_profit / total_stake * 100) if total_stake else Decimal("0")
        win_rate = Decimal(str(wins / decided * 100)) if decided else Decimal("0")

        breakdowns.append(
            SportBreakdown(
                sport=sport,
                total_bets=len(sport_bets),
                wins=wins,
                losses=losses,
                win_rate=win_rate.quantize(Decimal("0.01")),
                units_won=units_won.quantize(Decimal("0.01")),
                roi=roi.quantize(Decimal("0.01")),
            )
        )

    return sorted(breakdowns, key=lambda x: x.units_won, reverse=True)


def get_breakdown_by_bet_type(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[BetTypeBreakdown]:
    """Get performance breakdown by bet type."""
    client = get_supabase_client()
    query = (
        client.table("bets")
        .select("*")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
    )
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    types: dict[str, list[Bet]] = {}
    for bet in bets:
        types.setdefault(bet.bet_type, []).append(bet)

    breakdowns = []
    for bt, type_bets in types.items():
        wins = sum(1 for b in type_bets if b.result == BetResult.WIN)
        losses = sum(1 for b in type_bets if b.result == BetResult.LOSS)
        decided = wins + losses
        total_profit = sum(b.profit or Decimal("0") for b in type_bets)
        total_stake = sum(b.stake for b in type_bets)
        total_units = sum(b.units for b in type_bets)
        avg_unit = total_stake / total_units if total_units else Decimal("1")
        units_won = total_profit / avg_unit if avg_unit else Decimal("0")
        roi = (total_profit / total_stake * 100) if total_stake else Decimal("0")
        win_rate = Decimal(str(wins / decided * 100)) if decided else Decimal("0")

        breakdowns.append(
            BetTypeBreakdown(
                bet_type=bt,
                total_bets=len(type_bets),
                wins=wins,
                losses=losses,
                win_rate=win_rate.quantize(Decimal("0.01")),
                units_won=units_won.quantize(Decimal("0.01")),
                roi=roi.quantize(Decimal("0.01")),
            )
        )

    return sorted(breakdowns, key=lambda x: x.units_won, reverse=True)


def get_clv_summary(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> CLVSummary:
    """Get CLV (closing line value) analysis."""
    client = get_supabase_client()
    query = (
        client.table("bets")
        .select("*")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
        .not_.is_("clv_points", "null")
    )
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    if not bets:
        return CLVSummary()

    clv_values = [b.clv_points for b in bets if b.clv_points is not None]
    positive = sum(1 for c in clv_values if c > 0)
    negative = sum(1 for c in clv_values if c < 0)
    avg_clv = sum(clv_values) / Decimal(str(len(clv_values)))
    pos_rate = Decimal(str(positive / len(clv_values) * 100)) if clv_values else Decimal("0")

    return CLVSummary(
        avg_clv=avg_clv.quantize(Decimal("0.01")),
        positive_clv_count=positive,
        negative_clv_count=negative,
        positive_clv_rate=pos_rate.quantize(Decimal("0.01")),
    )


def get_user_bets_history(
    user_id: str,
    limit: int = 100,
) -> list[dict]:
    """Get user bet history as dicts for chart generation.

    Args:
        user_id: User's ID
        limit: Maximum number of bets to return

    Returns:
        List of bet dicts with profit info, ordered oldest first
    """
    client = get_supabase_client()
    result = (
        client.table("bets")
        .select("id, game, sport, bet_type, selection, odds, stake, profit, result, created_at, settled_at")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
        .order("settled_at", desc=True)
        .limit(limit)
        .execute()
    )

    bets_data = []
    for row in result.data:
        bets_data.append({
            "id": row.get("id"),
            "game": row.get("game"),
            "sport": row.get("sport"),
            "bet_type": row.get("bet_type"),
            "selection": row.get("selection"),
            "odds": row.get("odds"),
            "stake": float(row.get("stake", 0)),
            "profit": float(row.get("profit", 0)) if row.get("profit") else 0,
            "result": row.get("result"),
            "placed_at": row.get("created_at"),
            "settled_at": row.get("settled_at"),
        })

    return bets_data


def get_user_clv_history(
    user_id: str,
    limit: int = 100,
) -> list[dict]:
    """Get user CLV history for chart generation.

    Args:
        user_id: User's ID
        limit: Maximum number of bets to return

    Returns:
        List of dicts with CLV data for each bet
    """
    client = get_supabase_client()
    result = (
        client.table("bets")
        .select("id, game, selection, odds, clv_points, line_at_bet, closing_line, settled_at")
        .eq("user_id", user_id)
        .neq("result", BetResult.PENDING)
        .not_.is_("clv_points", "null")
        .order("settled_at", desc=True)
        .limit(limit)
        .execute()
    )

    clv_data = []
    for row in result.data:
        clv_points = row.get("clv_points")
        if clv_points is not None:
            clv_data.append({
                "id": row.get("id"),
                "description": f"{row.get('game', '')} - {row.get('selection', '')}",
                "odds": row.get("odds"),
                "clv_percentage": float(clv_points),
                "line_at_bet": float(row.get("line_at_bet")) if row.get("line_at_bet") else None,
                "closing_line": float(row.get("closing_line")) if row.get("closing_line") else None,
                "settled_at": row.get("settled_at"),
            })

    return clv_data
