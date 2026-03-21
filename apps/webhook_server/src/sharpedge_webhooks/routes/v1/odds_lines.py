"""Odds API helpers: game list, multi-book line comparison, prop market rows."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sharpedge_odds.client import OddsClient
from sharpedge_odds.constants import BOOKMAKER_DISPLAY_NAMES
from sharpedge_odds.models import Game, LineComparison
from sharpedge_shared.errors import ExternalAPIError
from sharpedge_shared.types import Sport

from sharpedge_webhooks.config import WebhookConfig

router = APIRouter(tags=["v1"])
_logger = logging.getLogger("sharpedge.webhooks.odds_lines")


def _config_odds_key() -> str:
    try:
        cfg = WebhookConfig()  # type: ignore[call-arg]
        return (cfg.odds_api_key or "").strip()
    except Exception:
        return ""


def _parse_sport(raw: str) -> Sport:
    key = raw.strip().upper()
    try:
        return Sport(key)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported sport: {raw}. Use NFL, NBA, MLB, NHL, NCAAF, NCAAB.",
        ) from e


def _client() -> OddsClient:
    api_key = _config_odds_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Odds API not configured (set odds_api_key / ODDS_API_KEY).",
        )
    return OddsClient(api_key=api_key)


def _game_summary(g: Game) -> dict[str, Any]:
    return {
        "id": g.id,
        "home_team": g.home_team,
        "away_team": g.away_team,
        "commence_time": g.commence_time.isoformat(),
        "sport_title": g.sport_title,
    }


def _comparison_payload(c: LineComparison) -> dict[str, Any]:
    def dump_lines(lines: list[Any]) -> list[dict[str, Any]]:
        return [x.model_dump() for x in lines]

    return {
        "game_id": c.game_id,
        "home_team": c.home_team,
        "away_team": c.away_team,
        "commence_time": c.commence_time.isoformat(),
        "spread_home": dump_lines(c.spread_home),
        "spread_away": dump_lines(c.spread_away),
        "total_over": dump_lines(c.total_over),
        "total_under": dump_lines(c.total_under),
        "moneyline_home": dump_lines(c.moneyline_home),
        "moneyline_away": dump_lines(c.moneyline_away),
    }


def _pick_game(
    client: OddsClient,
    sport: Sport,
    game_id: str | None,
    q: str | None,
    markets: list[str] | None,
) -> Game:
    games = client.get_odds(sport, markets=markets)
    if not games:
        raise HTTPException(status_code=404, detail="No games found for sport.")

    if game_id:
        for g in games:
            if g.id == game_id:
                return g
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")

    if q:
        found = client.find_game(q, sport=sport)
        if found is None:
            raise HTTPException(status_code=404, detail=f"No game matching query: {q!r}.")
        return found

    return games[0]


class PropRow(BaseModel):
    sportsbook: str
    sportsbook_display: str
    outcome_name: str
    point: float | None = None
    price: int


class PropsResponse(BaseModel):
    sport: str
    game_id: str
    market_key: str
    outcomes: list[PropRow] = Field(default_factory=list)


def _extract_props(game: Game, market_key: str) -> list[PropRow]:
    rows: list[PropRow] = []
    for book in game.bookmakers:
        disp = BOOKMAKER_DISPLAY_NAMES.get(book.key, book.title)
        for m in book.markets:
            if m.key != market_key:
                continue
            for o in m.outcomes:
                rows.append(
                    PropRow(
                        sportsbook=book.key,
                        sportsbook_display=disp,
                        outcome_name=o.name,
                        point=o.point,
                        price=o.price,
                    )
                )
    return rows


@router.get("/odds/games")
async def odds_games(
    sport: str = Query(..., description="NFL, NBA, MLB, NHL, NCAAF, NCAAB"),
    markets: str | None = Query(
        default=None,
        description="Comma-separated Odds API market keys; default h2h,spreads,totals",
    ),
) -> list[dict[str, Any]]:
    """List upcoming games for a sport (minimal fields for pickers)."""
    sp = _parse_sport(sport)
    mlist = (
        [x.strip() for x in markets.split(",") if x.strip()]
        if markets
        else None
    )
    try:
        client = _client()
        games = client.get_odds(sp, markets=mlist)
    except ExternalAPIError as e:
        _logger.warning("Odds API games: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    return [_game_summary(g) for g in games]


@router.get("/odds/line-comparison")
async def odds_line_comparison(
    sport: str = Query(...),
    game_id: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Fuzzy match team names if game_id omitted"),
    markets: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return spreads, totals, and moneylines across books with best-line flags."""
    sp = _parse_sport(sport)
    mlist = (
        [x.strip() for x in markets.split(",") if x.strip()]
        if markets
        else None
    )
    try:
        client = _client()
        game = _pick_game(client, sp, game_id, q, mlist)
        comp = client.get_line_comparison(game)
    except ExternalAPIError as e:
        _logger.warning("Odds API comparison: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e
    return _comparison_payload(comp)


@router.get("/odds/props", response_model=PropsResponse)
async def odds_props(
    sport: str = Query(...),
    market_key: str = Query(
        ...,
        min_length=1,
        description="Odds API alternate market key, e.g. player_points (NBA)",
    ),
    game_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> PropsResponse:
    """Fetch a single alternate market across books for one game."""
    sp = _parse_sport(sport)
    mk = market_key.strip()
    try:
        client = _client()
        game = _pick_game(client, sp, game_id, q, markets=["h2h", "spreads", "totals", mk])
    except ExternalAPIError as e:
        _logger.warning("Odds API props: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    rows = _extract_props(game, mk)
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No outcomes for market_key={mk!r}. Try another key or verify the sport.",
        )
    return PropsResponse(sport=sp.value, game_id=game.id, market_key=mk, outcomes=rows)
