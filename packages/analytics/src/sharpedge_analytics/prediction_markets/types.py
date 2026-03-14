"""Data types (dataclasses) for prediction market domain."""

from dataclasses import dataclass, field
from datetime import datetime

from .fees import Platform


@dataclass
class MarketOutcome:
    """A single outcome in a prediction market."""

    platform: Platform
    market_id: str
    outcome_id: str
    question: str  # Full market question
    outcome_label: str  # "Yes", "No", or specific option
    price: float  # Current price (0-1)
    volume_24h: float = 0
    liquidity: float = 0
    last_updated: datetime = field(default_factory=datetime.now)

    # Resolution details
    resolution_source: str = ""
    resolution_criteria: str = ""

    @property
    def implied_probability(self) -> float:
        """Price is the implied probability on prediction markets."""
        return self.price

    @property
    def complement_price(self) -> float:
        """Price of the opposite outcome (for arb calculations)."""
        return 1.0 - self.price


@dataclass
class CanonicalEvent:
    """A canonicalized event that may exist on multiple platforms.

    This maps equivalent outcomes across platforms despite different
    wording, resolution sources, or market structures.
    """

    canonical_id: str  # Our internal ID
    event_type: str  # "sports", "crypto", "politics", "economics"
    description: str  # Standardized description

    # Resolution criteria (must match for true equivalence)
    resolution_date: datetime | None = None
    resolution_source: str = ""
    resolution_criteria: str = ""

    # Mapped markets across platforms
    platform_markets: dict[Platform, MarketOutcome] = field(default_factory=dict)

    # Confidence in equivalence (0-1)
    equivalence_confidence: float = 1.0

    # Risk flags
    resolution_risk: str = ""  # Warning about differing resolution rules

    def add_market(self, outcome: MarketOutcome, confidence: float = 1.0) -> None:
        """Add a market outcome to this canonical event."""
        self.platform_markets[outcome.platform] = outcome
        # Reduce confidence if markets have different resolution criteria
        if outcome.resolution_criteria != self.resolution_criteria:
            self.equivalence_confidence = min(self.equivalence_confidence, confidence * 0.8)
            self.resolution_risk = "Resolution criteria may differ between platforms"
