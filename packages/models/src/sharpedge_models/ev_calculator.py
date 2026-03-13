"""Expected value calculation with statistically-grounded confidence metrics.

This module provides:
1. EV calculation with uncertainty quantification
2. Confidence intervals around probability estimates
3. Bayesian edge probability (P(true_edge > 0 | estimate))
4. Integration with backtesting calibration data

IMPORTANT: Confidence metrics are only as good as our calibration data.
When uncalibrated, we use theoretical uncertainty bounds and clearly
indicate that these are estimates, not empirically validated metrics.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger("sharpedge.models.ev_calculator")


class ConfidenceLevel(Enum):
    """Confidence classification based on P(edge > 0).

    These levels correspond to statistical confidence thresholds:
    - PREMIUM: >= 95% confidence (equivalent to 2σ)
    - HIGH: >= 84% confidence (equivalent to 1σ)
    - MEDIUM: >= 70% confidence
    - LOW: >= 55% confidence
    - SPECULATIVE: < 55% confidence
    """
    PREMIUM = "PREMIUM"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SPECULATIVE = "SPECULATIVE"


@dataclass
class UncertaintyEstimate:
    """Uncertainty quantification for a probability estimate.

    This uses a Beta distribution to model uncertainty around the
    probability estimate. The Beta distribution is the conjugate prior
    for binomial observations, making it ideal for win probability.
    """
    point_estimate: float  # Our best estimate of probability
    ci_lower: float  # Lower bound of 95% credible interval
    ci_upper: float  # Upper bound of 95% credible interval
    std_error: float  # Standard deviation of the estimate
    effective_sample_size: float  # Implicit sample size backing this estimate

    # Calibration status
    is_calibrated: bool  # Do we have backtest data for this?
    calibration_source: str  # "theoretical", "preliminary", "backtested"

    @property
    def ci_width(self) -> float:
        """Width of the confidence interval - measure of uncertainty."""
        return self.ci_upper - self.ci_lower


@dataclass
class EVCalculation:
    """Comprehensive EV calculation with uncertainty."""
    ev_percentage: float
    edge: float  # probability points
    implied_prob: float
    model_prob: float
    is_positive_ev: bool
    decimal_odds: float

    # Kelly criterion
    kelly_full: float
    kelly_half: float
    kelly_quarter: float

    # Uncertainty metrics
    uncertainty: UncertaintyEstimate

    # Derived confidence
    prob_edge_positive: float  # P(true_edge > 0) - THE key metric
    confidence_level: ConfidenceLevel

    # Supporting metrics
    breakeven_win_rate: float
    risk_reward_ratio: float

    @property
    def is_statistically_significant(self) -> bool:
        """Is the edge statistically significant at 95% level?"""
        return self.prob_edge_positive >= 0.95


@dataclass
class EVResult:
    """Value play result with full statistical backing."""
    game_id: str
    game: str
    market: str
    side: str
    ev_percentage: float
    edge: float
    model_line: float
    market_line: float
    model_prob: float
    market_prob: float
    odds: int

    # Statistical confidence
    confidence_level: str  # String version for serialization
    prob_edge_positive: float  # P(true_edge > 0)
    ci_lower: float  # Lower 95% CI on probability
    ci_upper: float  # Upper 95% CI on probability

    # Calibration status
    is_calibrated: bool
    calibration_note: str

    # Staking
    kelly_fraction: float
    half_kelly_stake: float

    # Metadata
    factors: dict[str, Any] = field(default_factory=dict)


def american_to_decimal(odds: int) -> float:
    """Convert American odds to decimal odds."""
    if odds > 0:
        return 1 + odds / 100
    else:
        return 1 + 100 / abs(odds)


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)


def estimate_probability_uncertainty(
    model_prob: float,
    model_type: str = "unknown",
    calibration_report: Any = None,
) -> UncertaintyEstimate:
    """Estimate uncertainty around a probability prediction.

    If we have calibration data, use it. Otherwise, use theoretical
    estimates based on typical model uncertainty.

    Args:
        model_prob: Point estimate of probability
        model_type: Type of model ("spread", "total", "moneyline")
        calibration_report: Optional CalibrationReport from backtesting

    Returns:
        UncertaintyEstimate with confidence intervals
    """
    # Check if we have calibration data
    if calibration_report is not None and calibration_report.is_reliable:
        # Use empirical calibration
        return _uncertainty_from_calibration(model_prob, calibration_report)

    # No calibration - use theoretical estimates
    # Model uncertainty depends on how far from 50% we are
    # Probabilities near 50% have higher uncertainty (harder to predict)
    # Probabilities near 0 or 1 have lower uncertainty

    # Use Beta distribution with pseudo-counts based on typical model accuracy
    # A model with ~55% accuracy on binary outcomes implies roughly
    # alpha=55, beta=45 worth of implicit observations

    # For uncalibrated models, we use conservative uncertainty
    # Assume effective sample size of ~50 (equivalent to limited data)
    effective_n = 50

    # Convert to Beta distribution parameters
    alpha = model_prob * effective_n
    beta = (1 - model_prob) * effective_n

    # Ensure minimum values for stability
    alpha = max(alpha, 1)
    beta = max(beta, 1)

    # Calculate credible interval
    ci_lower = float(stats.beta.ppf(0.025, alpha, beta))
    ci_upper = float(stats.beta.ppf(0.975, alpha, beta))
    std_error = float(stats.beta.std(alpha, beta))

    return UncertaintyEstimate(
        point_estimate=model_prob,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        std_error=std_error,
        effective_sample_size=effective_n,
        is_calibrated=False,
        calibration_source="theoretical",
    )


def _uncertainty_from_calibration(
    model_prob: float,
    calibration_report: Any,
) -> UncertaintyEstimate:
    """Extract uncertainty from calibration data."""
    # Find the calibration bin for this probability
    for cal_bin in calibration_report.bins:
        if cal_bin.prob_min <= model_prob < cal_bin.prob_max:
            # Adjust model probability based on calibration
            # If model systematically over/under predicts in this range,
            # adjust the effective probability

            calibration_adjustment = cal_bin.actual_rate - cal_bin.predicted_avg
            adjusted_prob = model_prob + calibration_adjustment

            # Clamp to valid range
            adjusted_prob = max(0.01, min(0.99, adjusted_prob))

            return UncertaintyEstimate(
                point_estimate=adjusted_prob,
                ci_lower=cal_bin.ci_lower,
                ci_upper=cal_bin.ci_upper,
                std_error=cal_bin.std_error,
                effective_sample_size=float(cal_bin.sample_size),
                is_calibrated=True,
                calibration_source="backtested",
            )

    # Probability outside calibration bins - use theoretical
    return estimate_probability_uncertainty(model_prob)


def calculate_prob_edge_positive(
    model_prob: float,
    implied_prob: float,
    uncertainty: UncertaintyEstimate,
) -> float:
    """Calculate P(true_edge > 0 | model_estimate).

    This is the key statistical question: given our model's estimate
    and its uncertainty, what is the probability that there is a
    true positive edge?

    Uses the Beta distribution of the model probability to calculate
    the probability that the true probability exceeds the implied.
    """
    # We model true_prob ~ Beta(alpha, beta) based on our uncertainty estimate
    # We want P(true_prob > implied_prob)

    # Estimate Beta parameters from our uncertainty
    if uncertainty.effective_sample_size > 0:
        alpha = model_prob * uncertainty.effective_sample_size
        beta = (1 - model_prob) * uncertainty.effective_sample_size

        # Ensure minimum values
        alpha = max(alpha, 1)
        beta = max(beta, 1)

        # P(true_prob > implied_prob) = 1 - CDF(implied_prob)
        prob_edge_positive = 1 - stats.beta.cdf(implied_prob, alpha, beta)
    else:
        # No uncertainty info - use point estimate only
        prob_edge_positive = 1.0 if model_prob > implied_prob else 0.0

    return float(prob_edge_positive)


def classify_confidence(prob_edge_positive: float) -> ConfidenceLevel:
    """Classify confidence based on P(edge > 0)."""
    if prob_edge_positive >= 0.95:
        return ConfidenceLevel.PREMIUM
    elif prob_edge_positive >= 0.84:
        return ConfidenceLevel.HIGH
    elif prob_edge_positive >= 0.70:
        return ConfidenceLevel.MEDIUM
    elif prob_edge_positive >= 0.55:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.SPECULATIVE


def calculate_ev(
    model_prob: float,
    odds: int,
    model_type: str = "spread",
    calibration_report: Any = None,
) -> EVCalculation:
    """Calculate expected value with full uncertainty quantification.

    Args:
        model_prob: Model's probability estimate (0-1)
        odds: American odds
        model_type: Type of bet for calibration lookup
        calibration_report: Optional calibration data from backtesting

    Returns:
        EVCalculation with uncertainty metrics
    """
    # Convert odds
    implied_prob = american_to_implied(odds)
    decimal_odds = american_to_decimal(odds)

    # Calculate uncertainty
    uncertainty = estimate_probability_uncertainty(
        model_prob, model_type, calibration_report
    )

    # Edge calculation
    edge = model_prob - implied_prob

    # EV calculation: EV = (prob_win * payout) - (prob_lose * stake)
    ev = model_prob * (decimal_odds - 1) - (1 - model_prob)
    ev_pct = ev * 100

    # Kelly criterion (using point estimate)
    if edge > 0 and decimal_odds > 1:
        kelly_full = edge / (decimal_odds - 1)
        kelly_full = max(0, min(kelly_full, 0.25))  # Cap at 25%
    else:
        kelly_full = 0.0

    # Calculate P(edge > 0)
    prob_edge_positive = calculate_prob_edge_positive(
        model_prob, implied_prob, uncertainty
    )

    # Classify confidence
    confidence_level = classify_confidence(prob_edge_positive)

    # Breakeven and risk/reward
    breakeven = implied_prob
    risk_reward = (decimal_odds - 1) / 1.0

    return EVCalculation(
        ev_percentage=round(ev_pct, 3),
        edge=round(edge * 100, 3),
        implied_prob=round(implied_prob * 100, 2),
        model_prob=round(model_prob * 100, 2),
        is_positive_ev=ev > 0,
        decimal_odds=round(decimal_odds, 3),
        kelly_full=round(kelly_full * 100, 2),
        kelly_half=round(kelly_full * 50, 2),
        kelly_quarter=round(kelly_full * 25, 2),
        uncertainty=uncertainty,
        prob_edge_positive=round(prob_edge_positive, 4),
        confidence_level=confidence_level,
        breakeven_win_rate=round(breakeven * 100, 2),
        risk_reward_ratio=round(risk_reward, 2),
    )


def find_value_plays(
    projections: list[dict],
    current_odds: list[dict],
    ev_threshold: float = 1.5,
    min_confidence: float = 0.55,
    calibration_reports: dict[str, Any] | None = None,
) -> list[EVResult]:
    """Find value plays with statistically-grounded confidence.

    Args:
        projections: List of model projections
        current_odds: List of current market odds
        ev_threshold: Minimum EV% to include
        min_confidence: Minimum P(edge > 0) to include
        calibration_reports: Dict of market_type -> CalibrationReport

    Returns:
        List of EVResult sorted by prob_edge_positive descending
    """
    value_plays: list[EVResult] = []

    for proj in projections:
        game_id = proj["game_id"]
        game_name = proj.get("game", "Unknown")

        # Find matching odds
        matching_odds = [o for o in current_odds if o.get("game_id") == game_id]
        if not matching_odds:
            continue

        odds_data = matching_odds[0]

        # Check spread
        if "spread_prob" in proj and "spread_odds" in odds_data:
            cal_report = calibration_reports.get("spread") if calibration_reports else None
            ev_calc = calculate_ev(
                proj["spread_prob"],
                odds_data["spread_odds"],
                "spread",
                cal_report,
            )

            if (ev_calc.ev_percentage >= ev_threshold and
                ev_calc.prob_edge_positive >= min_confidence):

                value_plays.append(_create_ev_result(
                    game_id=game_id,
                    game=game_name,
                    market="spread",
                    side=proj.get("spread_side", ""),
                    model_line=proj.get("model_spread", 0),
                    market_line=odds_data.get("market_spread", 0),
                    odds=odds_data["spread_odds"],
                    ev_calc=ev_calc,
                ))

        # Check total
        if "total_prob" in proj and "total_odds" in odds_data:
            cal_report = calibration_reports.get("total") if calibration_reports else None
            ev_calc = calculate_ev(
                proj["total_prob"],
                odds_data["total_odds"],
                "total",
                cal_report,
            )

            if (ev_calc.ev_percentage >= ev_threshold and
                ev_calc.prob_edge_positive >= min_confidence):

                value_plays.append(_create_ev_result(
                    game_id=game_id,
                    game=game_name,
                    market="total",
                    side=proj.get("total_side", ""),
                    model_line=proj.get("model_total", 0),
                    market_line=odds_data.get("market_total", 0),
                    odds=odds_data["total_odds"],
                    ev_calc=ev_calc,
                ))

        # Check moneyline
        if "ml_prob" in proj and "ml_odds" in odds_data:
            cal_report = calibration_reports.get("moneyline") if calibration_reports else None
            ev_calc = calculate_ev(
                proj["ml_prob"],
                odds_data["ml_odds"],
                "moneyline",
                cal_report,
            )

            if (ev_calc.ev_percentage >= ev_threshold and
                ev_calc.prob_edge_positive >= min_confidence):

                value_plays.append(_create_ev_result(
                    game_id=game_id,
                    game=game_name,
                    market="moneyline",
                    side=proj.get("ml_side", ""),
                    model_line=0,
                    market_line=0,
                    odds=odds_data["ml_odds"],
                    ev_calc=ev_calc,
                ))

    # Sort by P(edge > 0) - the statistically meaningful metric
    value_plays.sort(key=lambda x: x.prob_edge_positive, reverse=True)
    return value_plays


def _create_ev_result(
    game_id: str,
    game: str,
    market: str,
    side: str,
    model_line: float,
    market_line: float,
    odds: int,
    ev_calc: EVCalculation,
) -> EVResult:
    """Create EVResult from calculation."""
    calibration_note = (
        "Backtested - confidence based on historical model performance"
        if ev_calc.uncertainty.is_calibrated
        else "Theoretical - confidence based on statistical estimates (no backtest data yet)"
    )

    return EVResult(
        game_id=game_id,
        game=game,
        market=market,
        side=side,
        ev_percentage=ev_calc.ev_percentage,
        edge=ev_calc.edge,
        model_line=model_line,
        market_line=market_line,
        model_prob=ev_calc.model_prob,
        market_prob=ev_calc.implied_prob,
        odds=odds,
        confidence_level=ev_calc.confidence_level.value,
        prob_edge_positive=ev_calc.prob_edge_positive,
        ci_lower=ev_calc.uncertainty.ci_lower * 100,
        ci_upper=ev_calc.uncertainty.ci_upper * 100,
        is_calibrated=ev_calc.uncertainty.is_calibrated,
        calibration_note=calibration_note,
        kelly_fraction=ev_calc.kelly_full,
        half_kelly_stake=ev_calc.kelly_half,
    )
