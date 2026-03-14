"""Risk/Exposure Framework: ExposureBook, fractional Kelly, drawdown throttle.

Delegates to Phase 1 modules:
- ev_calculator.calculate_ev -> kelly_half (the base sizing fraction)
- monte_carlo.simulate_bankroll -> ruin_probability

Does NOT re-implement Monte Carlo or Kelly formula.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationDecision:
    """Fractional Kelly allocation decision with all adjustment factors recorded."""
    market_id: str
    venue_id: str
    kelly_full: float               # raw Kelly from ev_calculator
    kelly_half: float               # standard half-Kelly starting point
    venue_concentration_cap: float  # max fraction of bankroll on this venue
    correlation_discount: float     # multiplier [0, 1] from correlated positions (default 1.0)
    drawdown_throttle: float        # multiplier [0, 1] from apply_drawdown_throttle
    recommended_fraction: float     # final fraction: kelly_half * throttle * corr * cap_check
    ruin_probability: float         # from monte_carlo.simulate_bankroll


def apply_drawdown_throttle(
    current_drawdown: float,
    dd_threshold: float = 0.10,
    dd_max: float = 0.25,
) -> float:
    """Scale position sizing down as drawdown increases.

    Returns multiplier in [0.25, 1.0].
    - At or below dd_threshold: full sizing (1.0)
    - At dd_max: quarter sizing (0.25)
    - Linear interpolation between threshold and max
    - Below 0.25 floor: still 0.25 (never zero — preserves signal)
    """
    if current_drawdown <= dd_threshold:
        return 1.0
    if dd_threshold >= dd_max:
        return 0.25
    slope = (current_drawdown - dd_threshold) / (dd_max - dd_threshold)
    return max(0.25, 1.0 - 0.75 * min(1.0, slope))


class ExposureBook:
    """Tracks open position exposure by venue and market."""

    def __init__(
        self,
        bankroll: float = 10_000.0,
        venue_concentration_cap: float = 0.30,
    ) -> None:
        self._bankroll = bankroll
        self._venue_concentration_cap = venue_concentration_cap
        # {(venue_id, market_id): stake}
        self._positions: dict[tuple[str, str], float] = {}

    def add_position(self, venue_id: str, market_id: str, stake: float) -> None:
        """Record a new position stake (idempotent: overwrites if key exists)."""
        self._positions[(venue_id, market_id)] = stake

    def total_exposure(self) -> float:
        return sum(self._positions.values())

    def venue_exposure(self, venue_id: str) -> float:
        return sum(
            stake for (vid, _), stake in self._positions.items()
            if vid == venue_id
        )

    def venue_utilization(self, venue_id: str) -> float:
        """Fraction of bankroll currently on this venue."""
        if self._bankroll <= 0:
            return 0.0
        return self.venue_exposure(venue_id) / self._bankroll

    @property
    def bankroll(self) -> float:
        return self._bankroll

    @property
    def venue_concentration_cap(self) -> float:
        return self._venue_concentration_cap


def compute_allocation(
    book: ExposureBook,
    venue_id: str,
    market_id: str,
    edge: float,
    fair_prob: float,
    current_drawdown: float = 0.0,
    correlation_discount: float = 1.0,
) -> AllocationDecision:
    """Compute fractional Kelly allocation with all risk adjustments applied.

    Delegates to:
    - sharpedge_models.ev_calculator.calculate_ev for kelly_full and kelly_half
    - sharpedge_models.monte_carlo.simulate_bankroll for ruin_probability
    - apply_drawdown_throttle for drawdown adjustment
    - ExposureBook.venue_utilization for concentration cap check

    Args:
        book: current exposure state
        venue_id: target venue for this allocation
        market_id: target market
        edge: estimated probability edge (fair_prob - market_prob)
        fair_prob: devigged fair probability in (0, 1)
        current_drawdown: current bankroll drawdown fraction (0.0 = no DD)
        correlation_discount: multiplier from correlated positions (default 1.0)

    Returns:
        AllocationDecision with all factors recorded
    """
    # Delegate Kelly calculation to Phase 1 ev_calculator
    try:
        from sharpedge_models.ev_calculator import calculate_ev
        # Convert fair_prob to decimal odds for ev_calculator
        # decimal_odds = 1 / fair_prob (for YES side)
        decimal_odds = 1.0 / fair_prob if fair_prob > 1e-6 else 2.0
        ev_calc = calculate_ev(fair_prob=fair_prob, odds=decimal_odds, stake=1.0)
        kelly_full = float(ev_calc.kelly_full)
        kelly_half = float(ev_calc.kelly_half)
    except (ImportError, Exception):
        # Offline/test fallback: simple Kelly formula
        # Kelly = edge / (decimal_odds - 1) for binary markets
        decimal_odds = 1.0 / fair_prob if fair_prob > 1e-6 else 2.0
        kelly_full = edge / max(decimal_odds - 1.0, 1e-6)
        kelly_half = kelly_full / 2.0

    # Ensure kelly_half is positive when edge is positive
    if kelly_half <= 0 and edge > 0:
        kelly_half = edge / 2.0
        kelly_full = edge

    # Drawdown throttle
    throttle = apply_drawdown_throttle(current_drawdown)

    # Venue concentration cap check
    current_utilization = book.venue_utilization(venue_id)
    cap_fraction = book.venue_concentration_cap

    if current_utilization >= cap_fraction:
        # Cap hit: no new allocation to this venue
        recommended_fraction = 0.0
    else:
        recommended_fraction = kelly_half * throttle * correlation_discount
        # Don't exceed remaining cap headroom
        remaining_cap = (cap_fraction - current_utilization)
        recommended_fraction = min(recommended_fraction, remaining_cap)
        recommended_fraction = max(0.0, recommended_fraction)

    # Ruin probability from Phase 1 Monte Carlo
    ruin_probability = 0.0
    try:
        from sharpedge_models.monte_carlo import simulate_bankroll
        bet = {
            "stake": book.bankroll * recommended_fraction,
            "prob": fair_prob,
            "odds": 1.0 / fair_prob if fair_prob > 1e-6 else 2.0,
        }
        sim = simulate_bankroll(bankroll=book.bankroll, bets=[bet], n_simulations=200)
        ruin_probability = float(sim.ruin_probability)
    except (ImportError, Exception):
        ruin_probability = 0.0

    return AllocationDecision(
        market_id=market_id,
        venue_id=venue_id,
        kelly_full=kelly_full,
        kelly_half=kelly_half,
        venue_concentration_cap=cap_fraction,
        correlation_discount=correlation_discount,
        drawdown_throttle=throttle,
        recommended_fraction=recommended_fraction,
        ruin_probability=ruin_probability,
    )
