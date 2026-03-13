from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from sharpedge_shared.types import AlertType, BetResult, BetType, Sport, Tier


class User(BaseModel):
    id: str
    discord_id: str
    discord_username: str | None = None
    tier: Tier = Tier.FREE
    subscription_id: str | None = None
    bankroll: Decimal = Decimal("0")
    unit_size: Decimal = Decimal("0")
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Bet(BaseModel):
    id: str
    user_id: str

    # Bet details
    sport: Sport
    league: str | None = None
    game: str
    bet_type: BetType
    selection: str

    # Odds & stakes
    odds: int
    units: Decimal
    stake: Decimal
    potential_win: Decimal

    # Line tracking
    opening_line: Decimal | None = None
    line_at_bet: Decimal | None = None
    closing_line: Decimal | None = None
    clv_points: Decimal | None = None

    # Result
    result: BetResult = BetResult.PENDING
    profit: Decimal | None = None

    # Metadata
    sportsbook: str | None = None
    notes: str | None = None
    game_date: date | None = None
    created_at: datetime | None = None
    settled_at: datetime | None = None


class Usage(BaseModel):
    id: str
    user_id: str
    feature: str
    used_at: datetime | None = None


class Alert(BaseModel):
    id: str
    user_id: str
    alert_type: AlertType
    game_id: str | None = None
    content: str | None = None
    delivered_at: datetime | None = None


class Projection(BaseModel):
    id: str
    game_id: str
    sport: Sport
    home_team: str | None = None
    away_team: str | None = None
    projected_spread: Decimal | None = None
    projected_total: Decimal | None = None
    spread_confidence: Decimal | None = None
    total_confidence: Decimal | None = None
    calculated_at: datetime | None = None
    game_time: datetime | None = None


class OddsHistory(BaseModel):
    id: str
    game_id: str
    sportsbook: str
    bet_type: str
    line: Decimal | None = None
    odds: int | None = None
    recorded_at: datetime | None = None


# --- Result models for analytics queries ---


class PerformanceSummary(BaseModel):
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    win_rate: Decimal = Decimal("0")
    units_won: Decimal = Decimal("0")
    roi: Decimal = Decimal("0")
    avg_odds: int = 0


class SportBreakdown(BaseModel):
    sport: str
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: Decimal = Decimal("0")
    units_won: Decimal = Decimal("0")
    roi: Decimal = Decimal("0")


class BetTypeBreakdown(BaseModel):
    bet_type: str
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: Decimal = Decimal("0")
    units_won: Decimal = Decimal("0")
    roi: Decimal = Decimal("0")


class CLVSummary(BaseModel):
    avg_clv: Decimal = Decimal("0")
    positive_clv_count: int = 0
    negative_clv_count: int = 0
    positive_clv_rate: Decimal = Decimal("0")


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: datetime | None = None


class BankrollInfo(BaseModel):
    bankroll: Decimal
    unit_size: Decimal
    max_bet: Decimal
    sizing_table: dict[str, Field] = {}  # type: ignore[assignment]


class KellyResult(BaseModel):
    edge: Decimal
    implied_prob: Decimal
    true_prob: Decimal
    full_kelly: Decimal
    half_kelly: Decimal
    quarter_kelly: Decimal
