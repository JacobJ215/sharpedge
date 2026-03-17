"""Event dataclasses for the trading swarm pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class OpportunityEvent:
    market_id: str
    ticker: str
    category: str
    current_price: float
    liquidity: float
    time_to_resolution: timedelta
    price_momentum: float
    spread_ratio: float
    created_at: datetime = field(default_factory=_now)


@dataclass
class SignalScore:
    source: str
    sentiment: float
    confidence: float
    age_seconds: float


@dataclass
class ResearchEvent:
    market_id: str
    opportunity: OpportunityEvent
    narrative: str
    signal_scores: list[SignalScore]
    created_at: datetime = field(default_factory=_now)


@dataclass
class PredictionEvent:
    market_id: str
    research: ResearchEvent
    base_probability: float
    calibrated_probability: float
    edge: float
    confidence_score: float
    created_at: datetime = field(default_factory=_now)


@dataclass
class ApprovedEvent:
    market_id: str
    prediction: PredictionEvent
    created_at: datetime = field(default_factory=_now)


@dataclass
class ExecutionEvent:
    market_id: str
    direction: str  # 'yes' | 'no'
    size: float
    entry_price: float
    trading_mode: str
    created_at: datetime = field(default_factory=_now)


@dataclass
class ResolutionEvent:
    trade_id: str
    market_id: str
    actual_outcome: bool
    pnl: float
    trading_mode: str
    resolved_at: datetime = field(default_factory=_now)
