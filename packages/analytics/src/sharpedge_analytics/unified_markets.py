"""Unified Markets - Cross-platform analytics for sports betting and prediction markets.

This module applies lessons learned from prediction markets to traditional sportsbooks:
1. Fee-adjusted profit calculations (inspired by PM platform fees)
2. Market correlation and canonicalization (same event across platforms)
3. Real-time gap detection with configurable thresholds
4. Unified probability representation

Key insight: Prediction markets price in probabilities directly ($0.65 = 65%),
while sportsbooks use odds (-150 = 60% implied). This module normalizes both
into a common probability-first framework.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class MarketType(Enum):
    """Type of betting market."""
    SPORTSBOOK = "sportsbook"
    PREDICTION_MARKET = "prediction_market"
    EXCHANGE = "exchange"  # Betfair, etc.


@dataclass
class UnifiedOutcome:
    """A betting outcome in unified probability format.

    Normalizes sportsbook odds and prediction market prices to
    a common probability representation.
    """
    platform: str
    platform_type: MarketType
    market_id: str
    event_description: str
    outcome_description: str

    # Core pricing (always in probability format)
    probability: float  # 0-1, fair probability after vig removal
    raw_probability: float  # Implied probability before vig removal

    # Platform-specific
    american_odds: int | None = None  # For sportsbooks
    decimal_odds: float | None = None  # For exchanges
    price: float | None = None  # For prediction markets (0-1)

    # Liquidity/volume
    volume_24h: float = 0
    max_bet: float | None = None

    # Fees
    platform_fee_pct: float = 0

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_american_odds(
        cls,
        odds: int,
        platform: str,
        market_id: str,
        event_description: str,
        outcome_description: str,
        counterpart_odds: int | None = None,
    ) -> "UnifiedOutcome":
        """Create from American odds (sportsbook format).

        Args:
            odds: American odds (e.g., -150, +130)
            platform: Sportsbook name
            market_id: Market identifier
            event_description: Event description
            outcome_description: This outcome description
            counterpart_odds: Odds for the other side (to calculate vig)
        """
        # Convert to implied probability
        if odds > 0:
            raw_prob = 100 / (odds + 100)
        else:
            raw_prob = abs(odds) / (abs(odds) + 100)

        # Calculate fair probability if we have both sides
        if counterpart_odds is not None:
            if counterpart_odds > 0:
                counter_prob = 100 / (counterpart_odds + 100)
            else:
                counter_prob = abs(counterpart_odds) / (abs(counterpart_odds) + 100)

            total = raw_prob + counter_prob
            fair_prob = raw_prob / total  # Remove vig
        else:
            fair_prob = raw_prob  # Can't remove vig without both sides

        return cls(
            platform=platform,
            platform_type=MarketType.SPORTSBOOK,
            market_id=market_id,
            event_description=event_description,
            outcome_description=outcome_description,
            probability=fair_prob,
            raw_probability=raw_prob,
            american_odds=odds,
            decimal_odds=(odds / 100 + 1) if odds > 0 else (100 / abs(odds) + 1),
        )

    @classmethod
    def from_pm_price(
        cls,
        price: float,
        platform: str,
        market_id: str,
        event_description: str,
        outcome_description: str,
        platform_fee_pct: float = 0,
    ) -> "UnifiedOutcome":
        """Create from prediction market price.

        Args:
            price: Price in 0-1 format (probability)
            platform: Platform name (Kalshi, Polymarket)
            market_id: Market identifier
            event_description: Event description
            outcome_description: This outcome
            platform_fee_pct: Platform fee percentage
        """
        # PM prices are already probabilities
        # Adjust for platform fees to get effective probability
        effective_price = price * (1 + platform_fee_pct)

        return cls(
            platform=platform,
            platform_type=MarketType.PREDICTION_MARKET,
            market_id=market_id,
            event_description=event_description,
            outcome_description=outcome_description,
            probability=price,
            raw_probability=price,
            price=price,
            platform_fee_pct=platform_fee_pct,
        )


@dataclass
class UnifiedMarket:
    """A unified market that can exist across multiple platforms.

    This handles the canonicalization problem - matching "same event"
    across different platforms despite different naming.
    """
    canonical_id: str
    event_type: str  # "sports", "crypto", "politics", "economics"
    event_description: str
    resolution_time: datetime | None = None

    # Outcomes from all platforms
    outcomes: dict[str, list[UnifiedOutcome]] = field(default_factory=dict)
    # Key: platform name, Value: list of outcomes

    # Matching confidence
    cross_platform_confidence: float = 1.0

    def add_outcome(self, outcome: UnifiedOutcome) -> None:
        """Add an outcome from a platform."""
        if outcome.platform not in self.outcomes:
            self.outcomes[outcome.platform] = []
        self.outcomes[outcome.platform].append(outcome)

    def get_best_probability(self, side: str) -> tuple[str, float] | None:
        """Get the best probability for a side across all platforms.

        Args:
            side: Outcome description to match

        Returns:
            Tuple of (platform, probability) or None
        """
        best = None
        best_prob = 0.0

        for platform, outcomes in self.outcomes.items():
            for outcome in outcomes:
                if side.lower() in outcome.outcome_description.lower():
                    if outcome.probability > best_prob:
                        best_prob = outcome.probability
                        best = (platform, outcome.probability)

        return best

    def find_probability_gap(
        self,
        threshold_pct: float = 2.0,
    ) -> dict | None:
        """Find probability gaps across platforms.

        Similar to prediction market arb detection, but for sportsbooks.

        Args:
            threshold_pct: Minimum gap to flag

        Returns:
            Gap analysis if gap exceeds threshold, None otherwise
        """
        if len(self.outcomes) < 2:
            return None

        platforms = list(self.outcomes.keys())

        for i, platform_a in enumerate(platforms):
            for platform_b in platforms[i+1:]:
                outcomes_a = self.outcomes[platform_a]
                outcomes_b = self.outcomes[platform_b]

                # Compare probabilities for same outcomes
                for oa in outcomes_a:
                    for ob in outcomes_b:
                        if oa.outcome_description == ob.outcome_description:
                            gap = abs(oa.probability - ob.probability) * 100

                            if gap >= threshold_pct:
                                return {
                                    "platform_a": platform_a,
                                    "platform_b": platform_b,
                                    "outcome": oa.outcome_description,
                                    "prob_a": oa.probability,
                                    "prob_b": ob.probability,
                                    "gap_pct": round(gap, 2),
                                    "better_platform": platform_a if oa.probability > ob.probability else platform_b,
                                }

        return None


@dataclass
class CrossPlatformArbitrage:
    """Arbitrage opportunity across any combination of platforms.

    Works for:
    - Sportsbook vs Sportsbook (traditional arb)
    - Sportsbook vs Prediction Market (hybrid arb)
    - Prediction Market vs Prediction Market (PM arb)
    """
    market: UnifiedMarket

    # Buy side A
    platform_a: str
    platform_type_a: MarketType
    outcome_a: str
    probability_a: float

    # Buy side B
    platform_b: str
    platform_type_b: MarketType
    outcome_b: str
    probability_b: float

    # Profit metrics
    total_implied: float
    gross_profit_pct: float
    net_profit_pct: float  # After fees

    # Sizing
    stake_a_pct: float
    stake_b_pct: float

    # Risk
    execution_risk: float = 0.0  # 0-1
    settlement_risk: float = 0.0  # Different resolution rules

    @property
    def is_hybrid(self) -> bool:
        """Whether this spans sportsbooks and prediction markets."""
        return self.platform_type_a != self.platform_type_b

    @property
    def is_actionable(self) -> bool:
        """Whether this arb is worth executing."""
        return (
            self.net_profit_pct >= 0.5 and
            self.settlement_risk < 0.1 and
            self.execution_risk < 0.2
        )


def find_cross_platform_opportunities(
    sportsbook_odds: dict[str, dict[str, int]],  # {platform: {outcome: odds}}
    pm_prices: dict[str, dict[str, float]] | None = None,  # {platform: {outcome: price}}
    event_description: str = "",
    min_gap_pct: float = 2.0,
) -> list[dict]:
    """Find opportunities across sportsbooks and prediction markets.

    Args:
        sportsbook_odds: Sportsbook odds by platform and outcome
        pm_prices: Prediction market prices by platform and outcome
        event_description: Event description
        min_gap_pct: Minimum probability gap to flag

    Returns:
        List of opportunity dicts
    """
    opportunities = []

    # Create unified market
    market = UnifiedMarket(
        canonical_id=f"unified_{hash(event_description) % 10000}",
        event_type="sports" if pm_prices is None else "hybrid",
        event_description=event_description,
    )

    # Add sportsbook outcomes
    for platform, odds_by_outcome in sportsbook_odds.items():
        outcomes = list(odds_by_outcome.items())
        for i, (outcome, odds) in enumerate(outcomes):
            # Get counterpart for vig calculation
            counterpart = outcomes[1-i][1] if len(outcomes) == 2 else None

            unified = UnifiedOutcome.from_american_odds(
                odds=odds,
                platform=platform,
                market_id=f"{platform}_{event_description}",
                event_description=event_description,
                outcome_description=outcome,
                counterpart_odds=counterpart,
            )
            market.add_outcome(unified)

    # Add prediction market outcomes
    if pm_prices:
        for platform, prices_by_outcome in pm_prices.items():
            for outcome, price in prices_by_outcome.items():
                unified = UnifiedOutcome.from_pm_price(
                    price=price,
                    platform=platform,
                    market_id=f"{platform}_{event_description}",
                    event_description=event_description,
                    outcome_description=outcome,
                )
                market.add_outcome(unified)

    # Find gaps
    gap = market.find_probability_gap(threshold_pct=min_gap_pct)
    if gap:
        opportunities.append(gap)

    return opportunities


def calculate_hybrid_arb(
    sportsbook_odds: int,
    sportsbook_platform: str,
    pm_price: float,
    pm_platform: str,
    pm_fee_pct: float = 0.01,
    total_stake: float = 1000.0,
) -> CrossPlatformArbitrage | None:
    """Calculate arbitrage between a sportsbook and prediction market.

    This is a novel opportunity type - exploiting inefficiencies between
    traditional sportsbooks and prediction markets on the same event.

    Args:
        sportsbook_odds: American odds from sportsbook (for one side)
        sportsbook_platform: Sportsbook name
        pm_price: Prediction market price for opposite side
        pm_platform: Prediction market name
        pm_fee_pct: Prediction market fee percentage
        total_stake: Total amount to stake

    Returns:
        CrossPlatformArbitrage if opportunity exists, None otherwise
    """
    # Convert sportsbook odds to probability
    if sportsbook_odds > 0:
        sb_implied = 100 / (sportsbook_odds + 100)
    else:
        sb_implied = abs(sportsbook_odds) / (abs(sportsbook_odds) + 100)

    # PM price is probability of opposite side
    pm_implied = pm_price * (1 + pm_fee_pct)  # Adjust for fees

    # Total implied probability
    total_implied = sb_implied + pm_implied

    if total_implied >= 1.0:
        return None  # No arb

    # Calculate profit
    gross_profit_pct = (1 / total_implied - 1) * 100

    # Estimate net after fees
    # Sportsbook: assume no fee on winning
    # PM: fee already included in pm_implied
    net_profit_pct = gross_profit_pct * 0.95  # Conservative estimate

    # Calculate stakes
    stake_sb = (sb_implied / total_implied) * total_stake
    stake_pm = (pm_implied / total_implied) * total_stake

    return CrossPlatformArbitrage(
        market=UnifiedMarket(
            canonical_id="hybrid_arb",
            event_type="sports",
            event_description="Hybrid sportsbook/PM arbitrage",
        ),
        platform_a=sportsbook_platform,
        platform_type_a=MarketType.SPORTSBOOK,
        outcome_a="Sportsbook side",
        probability_a=sb_implied,
        platform_b=pm_platform,
        platform_type_b=MarketType.PREDICTION_MARKET,
        outcome_b="PM opposite side",
        probability_b=pm_implied,
        total_implied=round(total_implied, 4),
        gross_profit_pct=round(gross_profit_pct, 2),
        net_profit_pct=round(net_profit_pct, 2),
        stake_a_pct=round(stake_sb / total_stake * 100, 1),
        stake_b_pct=round(stake_pm / total_stake * 100, 1),
        settlement_risk=0.15,  # Inherent risk in hybrid arbs
    )


# ============================================
# UNIFIED SCANNING
# ============================================

class UnifiedScanner:
    """Scans for opportunities across all market types.

    Combines sportsbook arbitrage, prediction market arbitrage,
    and hybrid opportunities into a single scanner.
    """

    def __init__(self):
        self.sportsbook_data: dict[str, dict] = {}  # {event_id: {platform: odds}}
        self.pm_data: dict[str, dict] = {}  # {event_id: {platform: prices}}
        self.matches: dict[str, str] = {}  # {sb_event_id: pm_event_id}

    def add_sportsbook_odds(
        self,
        event_id: str,
        platform: str,
        home_odds: int,
        away_odds: int,
        home_team: str = "Home",
        away_team: str = "Away",
    ) -> None:
        """Add sportsbook odds for an event."""
        if event_id not in self.sportsbook_data:
            self.sportsbook_data[event_id] = {}

        self.sportsbook_data[event_id][platform] = {
            home_team: home_odds,
            away_team: away_odds,
        }

    def add_pm_prices(
        self,
        event_id: str,
        platform: str,
        yes_price: float,
        question: str = "",
    ) -> None:
        """Add prediction market prices for an event."""
        if event_id not in self.pm_data:
            self.pm_data[event_id] = {}

        self.pm_data[event_id][platform] = {
            "Yes": yes_price,
            "No": 1.0 - yes_price,
        }

    def match_events(
        self,
        sb_event_id: str,
        pm_event_id: str,
    ) -> None:
        """Match a sportsbook event to a prediction market event."""
        self.matches[sb_event_id] = pm_event_id

    def scan_all(
        self,
        min_profit_pct: float = 0.5,
    ) -> dict:
        """Scan for all opportunity types.

        Returns:
            Dict with sportsbook_arbs, pm_arbs, and hybrid_arbs
        """
        from sharpedge_analytics import scan_for_arbitrage

        results = {
            "sportsbook_arbs": [],
            "pm_arbs": [],
            "hybrid_arbs": [],
            "total_opportunities": 0,
        }

        # Sportsbook arbitrage
        for event_id, platforms in self.sportsbook_data.items():
            if len(platforms) < 2:
                continue

            # Get all odds for home/away
            home_odds = {}
            away_odds = {}
            teams = None

            for platform, odds in platforms.items():
                team_names = list(odds.keys())
                if teams is None:
                    teams = team_names

                home_odds[platform] = odds.get(teams[0], -110)
                away_odds[platform] = odds.get(teams[1], -110)

            arbs = scan_for_arbitrage(home_odds, away_odds)
            for arb in arbs:
                if arb.profit_percentage >= min_profit_pct:
                    results["sportsbook_arbs"].append({
                        "event_id": event_id,
                        "type": "sportsbook",
                        **arb.__dict__,
                    })

        # Hybrid arbitrage (sportsbook vs PM)
        for sb_event_id, pm_event_id in self.matches.items():
            if sb_event_id not in self.sportsbook_data:
                continue
            if pm_event_id not in self.pm_data:
                continue

            sb_data = self.sportsbook_data[sb_event_id]
            pm_data = self.pm_data[pm_event_id]

            # Try all combinations
            for sb_platform, sb_odds in sb_data.items():
                for pm_platform, pm_prices in pm_data.items():
                    # Try home vs PM No
                    for team, odds in sb_odds.items():
                        arb = calculate_hybrid_arb(
                            sportsbook_odds=odds,
                            sportsbook_platform=sb_platform,
                            pm_price=pm_prices.get("No", 0.5),
                            pm_platform=pm_platform,
                        )

                        if arb and arb.net_profit_pct >= min_profit_pct:
                            results["hybrid_arbs"].append({
                                "event_id": f"{sb_event_id}:{pm_event_id}",
                                "type": "hybrid",
                                "sportsbook": sb_platform,
                                "pm": pm_platform,
                                "profit_pct": arb.net_profit_pct,
                            })

        results["total_opportunities"] = (
            len(results["sportsbook_arbs"]) +
            len(results["pm_arbs"]) +
            len(results["hybrid_arbs"])
        )

        return results
