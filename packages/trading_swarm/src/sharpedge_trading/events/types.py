"""Event type definitions for trading pipeline."""
from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class OpportunityEvent:
    """Market opportunity identified by scanner."""
    market_id: str
    category: str
    kalshi_price: float
    liquidity: float
    time_to_resolution_hours: float
    title: str = ""
    anomaly_flags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)


@dataclass
class SignalScore:
    """Individual signal assessment."""
    source: str
    sentiment: float   # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    fetched_at: datetime = field(default_factory=_now)


@dataclass
class ResearchEvent:
    """Market research with multiple signals."""
    market_id: str
    category: str
    kalshi_price: float
    polymarket_price: float | None
    signals: list[SignalScore]
    narrative_summary: str
    time_to_resolution_hours: float
    created_at: datetime = field(default_factory=_now)


@dataclass
class PredictionEvent:
    """ML-calibrated prediction with edge."""
    market_id: str
    category: str
    kalshi_price: float
    calibrated_prob: float
    rf_base_prob: float
    llm_adjustment: float
    edge: float
    confidence_score: float
    time_to_resolution_hours: float
    research_snapshot: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)


@dataclass
class ApprovedEvent:
    """Trade approved for execution."""
    prediction: PredictionEvent
    approved_size_pct: float  # fraction of bankroll


@dataclass
class ExecutionEvent:
    """Trade executed in market."""
    market_id: str
    direction: str  # 'yes' | 'no'
    size_dollars: float
    entry_price: float
    category: str
    confidence_score: float
    trading_mode: str  # 'paper' | 'live'


@dataclass
class ResolutionEvent:
    """Market resolved with P&L."""
    market_id: str
    trade_id: str
    outcome: bool
    pnl: float
    entry_price: float
    exit_price: float
    trading_mode: str
