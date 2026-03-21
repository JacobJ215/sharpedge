"""POST /api/v1/bets — log a wager from a value play (web/mobile)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sharpedge_db.models import NewBetInput
from sharpedge_db.queries.bets import create_bet
from sharpedge_db.queries.users import (
    get_internal_user_id_by_supabase_auth,
    get_unit_size_for_user,
)
from sharpedge_db.queries.value_plays import get_value_play
from sharpedge_shared.types import BetType, Sport
from sharpedge_webhooks.routes.v1.deps import CurrentUser  # noqa: TC001

router = APIRouter(tags=["v1"])


class LogBetBody(BaseModel):
    """Body aligned with Flutter ``ApiService.logBet``."""

    play_id: str = Field(min_length=1)
    event: str = Field(min_length=1)
    market: str = ""
    team: str = Field(min_length=1)
    book: str = Field(min_length=1)
    stake: float = Field(gt=0, le=1_000_000)


def _potential_win_usd(stake: Decimal, american_odds: int) -> Decimal:
    """Profit if the bet wins (excludes returned stake). Matches bot odds_math."""
    if american_odds > 0:
        dec = Decimal("1") + Decimal(american_odds) / Decimal("100")
    else:
        dec = Decimal("1") + Decimal(100) / Decimal(abs(american_odds))
    return (stake * dec - stake).quantize(Decimal("0.01"))


def _bet_type_from_play(raw: str) -> BetType:
    key = (raw or "").strip().lower()
    mapping = {
        "spread": BetType.SPREAD,
        "total": BetType.TOTAL,
        "moneyline": BetType.MONEYLINE,
        "prop": BetType.PROP,
    }
    return mapping.get(key, BetType.SPREAD)


def _sport_from_play(raw: str) -> Sport:
    u = (raw or "").strip().upper()
    try:
        return Sport(u)
    except ValueError:
        return Sport.OTHER


@router.post("/bets", status_code=status.HTTP_201_CREATED)
async def log_bet(body: LogBetBody, current_user: CurrentUser) -> dict:
    """Create a pending bet row for the authenticated Supabase user."""
    supabase_uid = current_user["id"]
    internal_id = get_internal_user_id_by_supabase_auth(supabase_uid)
    if not internal_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    play = get_value_play(body.play_id)
    if not play:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Value play not found",
        )

    play_game = str(play.get("game") or "").strip().casefold()
    if play_game and body.event.strip().casefold() != play_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event does not match value play",
        )

    market_odds = play.get("market_odds")
    if market_odds is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Value play missing market_odds",
        )
    odds = round(float(market_odds))

    stake_dec = Decimal(str(body.stake)).quantize(Decimal("0.01"))
    unit_size = get_unit_size_for_user(internal_id)
    if unit_size > 0:
        units = (stake_dec / unit_size).quantize(Decimal("0.01"))
    else:
        units = (stake_dec / Decimal("50")).quantize(Decimal("0.01"))
        if units <= 0:
            units = Decimal("1")

    potential_win = _potential_win_usd(stake_dec, odds)
    selection = body.team.strip()
    game_label = body.event.strip()
    sport = _sport_from_play(str(play.get("sport") or ""))
    bet_type = _bet_type_from_play(str(play.get("bet_type") or ""))

    bet = create_bet(
        NewBetInput.for_log(
            user_id=internal_id,
            sport=sport,
            game=game_label,
            bet_type=bet_type,
            selection=selection,
            odds=odds,
            units=units,
            stake=stake_dec,
            potential_win=potential_win,
            sportsbook=body.book.strip(),
            notes=f"value_play_id={body.play_id}",
        ),
    )

    return {
        "id": bet.id,
        "game": bet.game,
        "selection": bet.selection,
        "stake": float(bet.stake),
        "odds": bet.odds,
        "units": float(bet.units),
    }
