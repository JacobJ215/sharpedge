"""Cross-platform prediction market arbitrage detection.

Supports Kalshi (CFTC-regulated) and Polymarket (crypto-based) with:
- Platform fee accounting
- Canonicalized outcome matching
- Real-time probability gap detection
- Precise sizing with fee-adjusted returns

Key concepts:
- Prediction markets price in probabilities directly ($0.65 = 65%)
- Arbitrage exists when: prob_yes_A + prob_no_B < 1.0 (after fees)
- Resolution risk: platforms may resolve "same" event differently
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable


class Platform(Enum):
    """Supported prediction market platforms."""
    KALSHI = "kalshi"
    POLYMARKET = "polymarket"
    POLYMARKET_US = "polymarket_us"
    METACULUS = "metaculus"
    PREDICTIT = "predictit"


@dataclass
class PlatformFees:
    """Fee structure for a prediction market platform."""

    platform: Platform
    taker_fee_pct: float  # Percentage fee on trades
    maker_fee_pct: float  # Fee for providing liquidity
    settlement_fee_per_contract: float  # Fee per winning contract
    withdrawal_fee: float  # Fixed withdrawal fee

    # Platform-specific fee formulas
    fee_formula: Callable[[float, float], float] | None = None

    def calculate_trade_fee(self, price: float, contracts: int) -> float:
        """Calculate fee for a trade.

        Args:
            price: Contract price (0-1 probability)
            contracts: Number of contracts

        Returns:
            Total fee in dollars
        """
        if self.fee_formula:
            return self.fee_formula(price, contracts)

        # Default: simple percentage
        notional = price * contracts
        return notional * self.taker_fee_pct

    def calculate_settlement_fee(self, winning_contracts: int) -> float:
        """Calculate fee on winning contracts."""
        return winning_contracts * self.settlement_fee_per_contract


# Platform fee configurations
def _kalshi_fee_formula(price: float, contracts: int) -> float:
    """Kalshi's probability-weighted fee: 0.07 × contracts × price × (1-price)"""
    return 0.07 * contracts * price * (1 - price)


def _kalshi_reduced_fee_formula(price: float, contracts: int) -> float:
    """Kalshi's reduced fee for S&P/Nasdaq markets: 0.035 multiplier"""
    return 0.035 * contracts * price * (1 - price)


PLATFORM_FEES: dict[Platform, PlatformFees] = {
    Platform.KALSHI: PlatformFees(
        platform=Platform.KALSHI,
        taker_fee_pct=0.01,  # ~1% effective (varies with price)
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.01,
        withdrawal_fee=2.0,  # $2 wire fee
        fee_formula=_kalshi_fee_formula,
    ),
    Platform.POLYMARKET: PlatformFees(
        platform=Platform.POLYMARKET,
        taker_fee_pct=0.0,  # No trading fees on standard markets
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.0,  # No settlement fee
        withdrawal_fee=0.50,  # Approximate gas fee
    ),
    Platform.POLYMARKET_US: PlatformFees(
        platform=Platform.POLYMARKET_US,
        taker_fee_pct=0.001,  # 0.10% = 10 bps
        maker_fee_pct=0.0,
        settlement_fee_per_contract=0.0,
        withdrawal_fee=0.50,
    ),
    Platform.PREDICTIT: PlatformFees(
        platform=Platform.PREDICTIT,
        taker_fee_pct=0.05,  # 5% on trades
        maker_fee_pct=0.05,
        settlement_fee_per_contract=0.10,  # 10% on profits
        withdrawal_fee=0.0,
    ),
}


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


@dataclass
class PredictionMarketArbitrage:
    """Cross-platform prediction market arbitrage opportunity."""

    canonical_event: CanonicalEvent

    # The two sides of the arb
    buy_yes_platform: Platform
    buy_yes_price: float  # Price to buy YES
    buy_no_platform: Platform
    buy_no_price: float  # Price to buy NO

    # Pre-fee metrics
    gross_probability_gap: float  # How much under 100%
    gross_profit_pct: float

    # Post-fee metrics
    net_profit_pct: float

    # Sizing instructions
    total_stake: float
    stake_yes: float
    stake_no: float
    guaranteed_return: float

    # Execution details
    detected_at: datetime = field(default_factory=datetime.now)
    estimated_window_seconds: int = 30  # How long opportunity lasts

    # Risk assessment
    resolution_risk: float = 0.0  # 0-1, risk of different resolution
    execution_risk: float = 0.0  # 0-1, risk of failed execution

    @property
    def is_actionable(self) -> bool:
        """Whether this arb is worth executing."""
        return (
            self.net_profit_pct >= 0.5 and  # At least 0.5% net profit
            self.resolution_risk < 0.1 and  # Low resolution risk
            self.execution_risk < 0.2  # Reasonable execution confidence
        )


def probability_to_price(prob: float) -> float:
    """Convert probability to prediction market price."""
    return prob


def price_to_probability(price: float) -> float:
    """Convert prediction market price to probability."""
    return price


def calculate_fee_adjusted_price(
    price: float,
    contracts: int,
    platform: Platform,
    is_buy: bool = True,
) -> float:
    """Calculate effective price after platform fees.

    Args:
        price: Raw contract price (0-1)
        contracts: Number of contracts
        platform: Trading platform
        is_buy: True if buying, False if selling

    Returns:
        Fee-adjusted effective price
    """
    fees = PLATFORM_FEES.get(platform)
    if not fees:
        return price

    trade_fee = fees.calculate_trade_fee(price, contracts)
    fee_per_contract = trade_fee / contracts if contracts > 0 else 0

    if is_buy:
        # Buying: effective price is higher
        return price + fee_per_contract
    else:
        # Selling: effective price is lower
        return price - fee_per_contract


def find_cross_platform_arbitrage(
    event: CanonicalEvent,
    stake: float = 1000.0,
    min_profit_pct: float = 0.5,
) -> PredictionMarketArbitrage | None:
    """Find arbitrage opportunity for a canonical event.

    Args:
        event: Canonicalized event with markets on multiple platforms
        stake: Total amount to stake
        min_profit_pct: Minimum profit percentage to consider

    Returns:
        Arbitrage opportunity if one exists, None otherwise
    """
    if len(event.platform_markets) < 2:
        return None

    platforms = list(event.platform_markets.keys())
    best_arb: PredictionMarketArbitrage | None = None
    best_profit = 0.0

    # Check all platform combinations
    for i, platform_a in enumerate(platforms):
        for platform_b in platforms[i + 1:]:
            market_a = event.platform_markets[platform_a]
            market_b = event.platform_markets[platform_b]

            # Try both directions:
            # 1. Buy YES on A, buy NO on B
            arb = _check_arb_direction(
                event, market_a, market_b, stake,
                buy_yes_on_a=True,
            )
            if arb and arb.net_profit_pct > best_profit:
                best_arb = arb
                best_profit = arb.net_profit_pct

            # 2. Buy NO on A, buy YES on B
            arb = _check_arb_direction(
                event, market_a, market_b, stake,
                buy_yes_on_a=False,
            )
            if arb and arb.net_profit_pct > best_profit:
                best_arb = arb
                best_profit = arb.net_profit_pct

    if best_arb and best_arb.net_profit_pct >= min_profit_pct:
        return best_arb

    return None


def _check_arb_direction(
    event: CanonicalEvent,
    market_a: MarketOutcome,
    market_b: MarketOutcome,
    stake: float,
    buy_yes_on_a: bool,
) -> PredictionMarketArbitrage | None:
    """Check if arbitrage exists in one direction."""

    if buy_yes_on_a:
        yes_price = market_a.price
        yes_platform = market_a.platform
        no_price = market_b.complement_price
        no_platform = market_b.platform
    else:
        yes_price = market_b.price
        yes_platform = market_b.platform
        no_price = market_a.complement_price
        no_platform = market_a.platform

    # Calculate fee-adjusted prices
    # Assume 100 contracts for fee calculation
    contracts = 100

    adj_yes_price = calculate_fee_adjusted_price(
        yes_price, contracts, yes_platform, is_buy=True
    )
    adj_no_price = calculate_fee_adjusted_price(
        no_price, contracts, no_platform, is_buy=True
    )

    # Gross arbitrage check (before fees)
    gross_total = yes_price + no_price
    if gross_total >= 1.0:
        return None  # No gross arb

    gross_gap = 1.0 - gross_total
    gross_profit_pct = (1.0 / gross_total - 1.0) * 100

    # Net arbitrage check (after fees)
    net_total = adj_yes_price + adj_no_price
    if net_total >= 1.0:
        return None  # Fees eliminate arb

    net_profit_pct = (1.0 / net_total - 1.0) * 100

    # Calculate optimal stake allocation
    stake_yes = stake * (adj_yes_price / net_total)
    stake_no = stake * (adj_no_price / net_total)

    # Guaranteed return (either outcome wins)
    guaranteed_return = stake / net_total

    return PredictionMarketArbitrage(
        canonical_event=event,
        buy_yes_platform=yes_platform,
        buy_yes_price=yes_price,
        buy_no_platform=no_platform,
        buy_no_price=no_price,
        gross_probability_gap=gross_gap,
        gross_profit_pct=round(gross_profit_pct, 3),
        net_profit_pct=round(net_profit_pct, 3),
        total_stake=stake,
        stake_yes=round(stake_yes, 2),
        stake_no=round(stake_no, 2),
        guaranteed_return=round(guaranteed_return, 2),
        resolution_risk=1.0 - event.equivalence_confidence,
    )


def detect_probability_gap(
    price_yes_a: float,
    price_no_b: float,
    platform_a: Platform,
    platform_b: Platform,
    threshold_pct: float = 2.0,
) -> dict | None:
    """Detect if probability gap exceeds threshold.

    This is the core detection logic for real-time scanning.

    Args:
        price_yes_a: YES price on platform A
        price_no_b: NO price on platform B (or 1 - YES price)
        platform_a: First platform
        platform_b: Second platform
        threshold_pct: Minimum gap to flag (default 2%)

    Returns:
        Gap analysis dict if gap exceeds threshold, None otherwise
    """
    total_implied = price_yes_a + price_no_b
    gap_pct = (1.0 - total_implied) * 100

    if gap_pct < threshold_pct:
        return None

    # Account for fees
    fees_a = PLATFORM_FEES.get(platform_a)
    fees_b = PLATFORM_FEES.get(platform_b)

    total_fee_pct = 0.0
    if fees_a:
        total_fee_pct += fees_a.taker_fee_pct * 100
    if fees_b:
        total_fee_pct += fees_b.taker_fee_pct * 100

    net_gap_pct = gap_pct - total_fee_pct

    return {
        "gross_gap_pct": round(gap_pct, 2),
        "net_gap_pct": round(net_gap_pct, 2),
        "total_implied": round(total_implied, 4),
        "is_profitable": net_gap_pct > 0,
        "platform_a": platform_a.value,
        "platform_b": platform_b.value,
        "price_yes_a": price_yes_a,
        "price_no_b": price_no_b,
    }


class MarketCorrelationNetwork:
    """Network for tracking correlated/equivalent markets.

    This handles the canonicalization problem: mapping markets that
    resolve to the same outcome despite different wording.
    """

    def __init__(self):
        self.canonical_events: dict[str, CanonicalEvent] = {}
        self.market_to_event: dict[str, str] = {}  # market_id -> canonical_id

        # Keyword patterns for matching similar events
        self.matching_patterns: dict[str, list[str]] = {
            "btc_100k": ["bitcoin", "btc", "100k", "100,000"],
            "trump_2024": ["trump", "president", "2024", "election"],
            "fed_rate": ["fed", "federal reserve", "interest rate", "fomc"],
        }

    def add_market(self, outcome: MarketOutcome) -> str:
        """Add a market and attempt to match to canonical event.

        Returns:
            canonical_id of matched or created event
        """
        # Check if already mapped
        key = f"{outcome.platform.value}:{outcome.market_id}"
        if key in self.market_to_event:
            return self.market_to_event[key]

        # Try to match to existing canonical event
        matched_event = self._find_matching_event(outcome)

        if matched_event:
            matched_event.add_market(outcome)
            self.market_to_event[key] = matched_event.canonical_id
            return matched_event.canonical_id

        # Create new canonical event
        canonical_id = f"event_{len(self.canonical_events)}"
        event = CanonicalEvent(
            canonical_id=canonical_id,
            event_type=self._infer_event_type(outcome),
            description=outcome.question,
            resolution_source=outcome.resolution_source,
            resolution_criteria=outcome.resolution_criteria,
        )
        event.add_market(outcome)

        self.canonical_events[canonical_id] = event
        self.market_to_event[key] = canonical_id

        return canonical_id

    def _find_matching_event(self, outcome: MarketOutcome) -> CanonicalEvent | None:
        """Find existing canonical event matching this market."""
        question_lower = outcome.question.lower()

        for event in self.canonical_events.values():
            # Check for high text similarity
            if self._calculate_similarity(question_lower, event.description.lower()) > 0.7:
                return event

            # Check pattern matching
            for pattern_key, keywords in self.matching_patterns.items():
                if all(kw in question_lower for kw in keywords):
                    if all(kw in event.description.lower() for kw in keywords):
                        return event

        return None

    def _calculate_similarity(self, text_a: str, text_b: str) -> float:
        """Simple Jaccard similarity between texts."""
        words_a = set(text_a.split())
        words_b = set(text_b.split())

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0

    def _infer_event_type(self, outcome: MarketOutcome) -> str:
        """Infer event type from market question."""
        question_lower = outcome.question.lower()

        if any(kw in question_lower for kw in ["bitcoin", "btc", "eth", "crypto"]):
            return "crypto"
        elif any(kw in question_lower for kw in ["president", "election", "congress", "senate"]):
            return "politics"
        elif any(kw in question_lower for kw in ["fed", "gdp", "inflation", "unemployment"]):
            return "economics"
        elif any(kw in question_lower for kw in ["game", "team", "match", "championship"]):
            return "sports"

        return "other"

    def scan_for_arbitrage(
        self,
        min_profit_pct: float = 0.5,
        stake: float = 1000.0,
    ) -> list[PredictionMarketArbitrage]:
        """Scan all canonical events for arbitrage opportunities."""
        opportunities = []

        for event in self.canonical_events.values():
            arb = find_cross_platform_arbitrage(event, stake, min_profit_pct)
            if arb:
                opportunities.append(arb)

        # Sort by net profit descending
        opportunities.sort(key=lambda x: x.net_profit_pct, reverse=True)
        return opportunities

    def get_multi_platform_events(self) -> list[CanonicalEvent]:
        """Get events available on multiple platforms (arb candidates)."""
        return [
            event for event in self.canonical_events.values()
            if len(event.platform_markets) >= 2
        ]


def calculate_sizing_instructions(
    arb: PredictionMarketArbitrage,
    bankroll: float,
    max_bet_pct: float = 0.05,
) -> dict:
    """Calculate precise sizing instructions for an arbitrage trade.

    Args:
        arb: The arbitrage opportunity
        bankroll: Total available bankroll
        max_bet_pct: Maximum percentage of bankroll to risk

    Returns:
        Detailed sizing instructions
    """
    max_stake = bankroll * max_bet_pct

    # Adjust stake if arb stake exceeds max
    if arb.total_stake > max_stake:
        scale_factor = max_stake / arb.total_stake
        stake_yes = arb.stake_yes * scale_factor
        stake_no = arb.stake_no * scale_factor
        total_stake = max_stake
        guaranteed_return = arb.guaranteed_return * scale_factor
    else:
        stake_yes = arb.stake_yes
        stake_no = arb.stake_no
        total_stake = arb.total_stake
        guaranteed_return = arb.guaranteed_return

    profit = guaranteed_return - total_stake

    # Calculate contracts (assuming $1 contract value)
    contracts_yes = int(stake_yes / arb.buy_yes_price)
    contracts_no = int(stake_no / arb.buy_no_price)

    return {
        "action": "EXECUTE_ARB",
        "total_stake": round(total_stake, 2),
        "guaranteed_profit": round(profit, 2),
        "roi_pct": round(arb.net_profit_pct, 2),
        "instructions": [
            {
                "platform": arb.buy_yes_platform.value,
                "action": "BUY",
                "side": "YES",
                "price": arb.buy_yes_price,
                "amount": round(stake_yes, 2),
                "contracts": contracts_yes,
            },
            {
                "platform": arb.buy_no_platform.value,
                "action": "BUY",
                "side": "NO",
                "price": arb.buy_no_price,
                "amount": round(stake_no, 2),
                "contracts": contracts_no,
            },
        ],
        "risk_warning": arb.canonical_event.resolution_risk or None,
        "time_sensitive": arb.estimated_window_seconds < 60,
        "estimated_window_seconds": arb.estimated_window_seconds,
    }
