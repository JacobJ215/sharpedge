"""Pydantic models for Odds API responses and processed data."""

from datetime import datetime

from pydantic import BaseModel


class Outcome(BaseModel):
    name: str
    price: int  # American odds
    point: float | None = None  # Spread/total line


class Market(BaseModel):
    key: str  # "h2h", "spreads", "totals"
    last_update: datetime | None = None
    outcomes: list[Outcome]


class Bookmaker(BaseModel):
    key: str
    title: str
    last_update: datetime | None = None
    markets: list[Market]


class Game(BaseModel):
    id: str
    sport_key: str
    sport_title: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: list[Bookmaker]


class FormattedLine(BaseModel):
    """A processed line ready for display."""

    sportsbook: str
    sportsbook_display: str
    side: str  # Team name or "Over"/"Under"
    line: float | None = None  # Spread/total number
    odds: int
    is_best: bool = False


class LineComparison(BaseModel):
    """Processed line comparison for a game."""

    game_id: str
    home_team: str
    away_team: str
    commence_time: datetime
    spread_home: list[FormattedLine] = []
    spread_away: list[FormattedLine] = []
    total_over: list[FormattedLine] = []
    total_under: list[FormattedLine] = []
    moneyline_home: list[FormattedLine] = []
    moneyline_away: list[FormattedLine] = []
