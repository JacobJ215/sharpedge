"""Supabase-backed bet queries.

Inserts, results, history, and portfolio slices.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sharpedge_db.client import get_supabase_client
from sharpedge_db.models import (
    Bet,
    BetHistoryParams,
    BetTypeBreakdown,
    CLVSummary,
    NewBetInput,
    PerformanceSummary,
    SportBreakdown,
)
from sharpedge_shared.types import BetResult


def _settled_group_core(group: list[Bet]) -> dict[str, int | Decimal]:
    """Shared win/loss, ROI, and units-won math for settled bet groups."""
    wins = sum(1 for b in group if b.result == BetResult.WIN)
    losses = sum(1 for b in group if b.result == BetResult.LOSS)
    decided = wins + losses
    total_profit = sum(b.profit or Decimal("0") for b in group)
    total_stake = sum(b.stake for b in group)
    roi = (total_profit / total_stake * 100) if total_stake else Decimal("0")
    win_rate = Decimal(str(wins / decided * 100)) if decided else Decimal("0")
    total_units = sum(b.units for b in group)
    avg_unit = total_stake / total_units if total_units else Decimal("1")
    units_won = total_profit / avg_unit if avg_unit else Decimal("0")
    return {
        "wins": wins,
        "losses": losses,
        "n": len(group),
        "win_rate_q": win_rate.quantize(Decimal("0.01")),
        "roi_q": roi.quantize(Decimal("0.01")),
        "units_won_q": units_won.quantize(Decimal("0.01")),
    }


def create_bet(bet: NewBetInput) -> Bet:
    """Create a new bet record."""
    client = get_supabase_client()
    data: dict = {
        "user_id": bet.user_id,
        "sport": bet.sport,
        "game": bet.game,
        "bet_type": bet.bet_type,
        "selection": bet.selection,
        "odds": bet.odds,
        "units": float(bet.units),
        "stake": float(bet.stake),
        "potential_win": float(bet.potential_win),
        "result": BetResult.PENDING,
    }
    if bet.league:
        data["league"] = bet.league
    if bet.sportsbook:
        data["sportsbook"] = bet.sportsbook
    if bet.notes:
        data["notes"] = bet.notes
    if bet.game_date:
        data["game_date"] = bet.game_date.isoformat()
    if bet.opening_line is not None:
        data["opening_line"] = float(bet.opening_line)
    if bet.line_at_bet is not None:
        data["line_at_bet"] = float(bet.line_at_bet)

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
        "settled_at": datetime.now(UTC).isoformat(),
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


def get_bet_history(params: BetHistoryParams) -> list[Bet]:
    """Get bet history with optional filters."""
    client = get_supabase_client()
    query = client.table("bets").select("*").eq("user_id", params.user_id)

    if params.sport:
        query = query.eq("sport", params.sport)
    if params.bet_type:
        query = query.eq("bet_type", params.bet_type)
    if params.start_date:
        query = query.gte("created_at", params.start_date.isoformat())
    if params.end_date:
        query = query.lte("created_at", params.end_date.isoformat())

    hi = params.offset + params.limit - 1
    result = query.order("created_at", desc=True).range(params.offset, hi).execute()
    return [Bet(**row) for row in result.data]


def _get_date_range(period: str = "all") -> tuple[date, date]:
    """Get start/end dates for a period."""
    today = datetime.now(UTC).date()
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
    query = client.table("bets").select("*").eq("user_id", user_id).neq("result", BetResult.PENDING)
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
    query = client.table("bets").select("*").eq("user_id", user_id).neq("result", BetResult.PENDING)
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
        c = _settled_group_core(sport_bets)
        breakdowns.append(
            SportBreakdown(
                sport=str(sport),
                total_bets=int(c["n"]),
                wins=int(c["wins"]),
                losses=int(c["losses"]),
                win_rate=c["win_rate_q"],
                units_won=c["units_won_q"],
                roi=c["roi_q"],
            ),
        )

    return sorted(breakdowns, key=lambda x: x.units_won, reverse=True)


def get_breakdown_by_bet_type(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[BetTypeBreakdown]:
    """Get performance breakdown by bet type."""
    client = get_supabase_client()
    query = client.table("bets").select("*").eq("user_id", user_id).neq("result", BetResult.PENDING)
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
        c = _settled_group_core(type_bets)
        breakdowns.append(
            BetTypeBreakdown(
                bet_type=str(bt),
                total_bets=int(c["n"]),
                wins=int(c["wins"]),
                losses=int(c["losses"]),
                win_rate=c["win_rate_q"],
                units_won=c["units_won_q"],
                roi=c["roi_q"],
            ),
        )

    return sorted(breakdowns, key=lambda x: x.units_won, reverse=True)


def american_odds_juice_bucket(american_odds: int) -> str:
    """Bucket American odds for performance-by-juice views (compact labels)."""
    o = int(american_odds)
    if o <= -150:
        return "<= -150"
    if o <= -110:
        return "-149 to -110"
    if o <= 100:
        return "-109 to +100"
    if o <= 200:
        return "+101 to +200"
    return ">= +201"


def get_breakdown_by_sportsbook(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """Settled bets only — performance grouped by ``sportsbook``."""
    client = get_supabase_client()
    query = client.table("bets").select("*").eq("user_id", user_id).neq("result", BetResult.PENDING)
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    books: dict[str, list[Bet]] = {}
    for bet in bets:
        key = (bet.sportsbook or "").strip() or "(none)"
        books.setdefault(key, []).append(bet)

    rows: list[dict] = []
    for book, book_bets in books.items():
        c = _settled_group_core(book_bets)
        rows.append(
            {
                "sportsbook": book,
                "total_bets": int(c["n"]),
                "wins": int(c["wins"]),
                "losses": int(c["losses"]),
                "win_rate": float(c["win_rate_q"]),
                "roi": float(c["roi_q"]),
            },
        )

    return sorted(rows, key=lambda r: r["total_bets"], reverse=True)


def get_breakdown_by_juice_bucket(
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    """Settled bets only — grouped by American odds / juice bucket."""
    client = get_supabase_client()
    query = client.table("bets").select("*").eq("user_id", user_id).neq("result", BetResult.PENDING)
    if start_date:
        query = query.gte("created_at", start_date.isoformat())
    if end_date:
        query = query.lte("created_at", end_date.isoformat())

    result = query.execute()
    bets = [Bet(**row) for row in result.data]

    buckets: dict[str, list[Bet]] = {}
    for bet in bets:
        key = american_odds_juice_bucket(int(bet.odds))
        buckets.setdefault(key, []).append(bet)

    # Stable display order (favorites first)
    order = [
        "<= -150",
        "-149 to -110",
        "-109 to +100",
        "+101 to +200",
        ">= +201",
    ]

    rows: list[dict] = []
    for bucket in order:
        bucket_bets = buckets.get(bucket)
        if not bucket_bets:
            continue
        c = _settled_group_core(bucket_bets)
        rows.append(
            {
                "bucket": bucket,
                "total_bets": int(c["n"]),
                "wins": int(c["wins"]),
                "losses": int(c["losses"]),
                "win_rate": float(c["win_rate_q"]),
                "roi": float(c["roi_q"]),
            },
        )

    return rows


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


def _history_row_from_supabase(row: dict) -> dict:
    """Map a Supabase bet row to the portfolio/history API shape."""
    clv_points = row.get("clv_points")
    raw_profit = row.get("profit")
    profit_val = 0.0
    if raw_profit is not None:
        profit_val = float(raw_profit)
    item = {
        "id": row.get("id"),
        "game": row.get("game"),
        "sport": row.get("sport"),
        "bet_type": row.get("bet_type"),
        "selection": row.get("selection"),
        "odds": row.get("odds"),
        "stake": float(row.get("stake", 0)),
        "profit": profit_val,
        "result": row.get("result"),
        "placed_at": row.get("created_at"),
        "settled_at": row.get("settled_at"),
        "sportsbook": row.get("sportsbook"),
        "clv_points": float(clv_points) if clv_points is not None else None,
    }
    if clv_points is not None:
        item["clv"] = float(clv_points)
    return item


def get_user_bets_history(
    user_id: str,
    limit: int = 100,
) -> list[dict]:
    """Get user bet rows for portfolio, bankroll, and charts.

    Includes **pending** bets so active positions surface in the API. Newest
    first by ``created_at``. Adds ``clv`` alias when ``clv_points`` is set.
    """
    client = get_supabase_client()
    result = (
        client.table("bets")
        .select(
            "id, game, sport, bet_type, selection, odds, stake, profit, "
            "result, created_at, settled_at, sportsbook, clv_points",
        )
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [_history_row_from_supabase(row) for row in (result.data or [])]


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
    clv_cols = "id, game, selection, odds, clv_points, line_at_bet, closing_line, settled_at"
    result = (
        client.table("bets")
        .select(clv_cols)
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
        if clv_points is None:
            continue
        game = row.get("game", "") or ""
        sel = row.get("selection", "") or ""
        lat = row.get("line_at_bet")
        clo = row.get("closing_line")
        clv_data.append(
            {
                "id": row.get("id"),
                "description": f"{game} - {sel}",
                "odds": row.get("odds"),
                "clv_percentage": float(clv_points),
                "line_at_bet": float(lat) if lat else None,
                "closing_line": float(clo) if clo else None,
                "settled_at": row.get("settled_at"),
            },
        )

    return clv_data
