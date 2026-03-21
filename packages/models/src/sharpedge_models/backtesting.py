"""Backtesting engine for model calibration and confidence estimation.

This module provides the infrastructure to:
1. Run historical backtests on model predictions
2. Calculate calibration curves (predicted vs actual outcomes)
3. Generate statistically valid confidence metrics
4. Store and update calibration data over time

Without backtesting data, confidence metrics are theoretical estimates only.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np
from scipy import stats

logger = logging.getLogger("sharpedge.models.backtesting")


class CalibrationStatus(Enum):
    """Status of model calibration."""

    UNCALIBRATED = "uncalibrated"  # No backtest data available
    PRELIMINARY = "preliminary"  # <100 samples, high uncertainty
    CALIBRATED = "calibrated"  # 100-1000 samples, moderate confidence
    WELL_CALIBRATED = "well_calibrated"  # 1000+ samples, high confidence


@dataclass
class BacktestResult:
    """Result of a single backtest prediction."""

    prediction_id: str
    timestamp: datetime
    market_type: str  # "spread", "total", "moneyline"
    sport: str
    predicted_probability: float
    predicted_edge: float
    odds: int
    outcome: bool | None  # True=win, False=loss, None=pending
    closing_line: float | None  # For CLV calculation
    model_version: str = ""  # trained_at timestamp string (MODEL-01)


@dataclass
class CalibrationBin:
    """Calibration data for a probability bin."""

    prob_min: float
    prob_max: float
    predicted_avg: float  # Average predicted probability in bin
    actual_rate: float  # Actual win rate observed
    sample_size: int
    std_error: float  # Standard error of actual_rate
    ci_lower: float  # 95% CI lower bound
    ci_upper: float  # 95% CI upper bound


@dataclass
class CalibrationReport:
    """Full calibration report for a model."""

    market_type: str
    sport: str | None  # None = all sports combined
    total_predictions: int
    total_resolved: int
    bins: list[CalibrationBin]
    brier_score: float  # Lower is better, 0 = perfect
    calibration_error: float  # Mean absolute calibration error
    discrimination: float  # AUC-ROC or similar
    status: CalibrationStatus
    last_updated: datetime

    @property
    def is_reliable(self) -> bool:
        """Check if calibration data is reliable enough for production use."""
        return (
            self.status in (CalibrationStatus.CALIBRATED, CalibrationStatus.WELL_CALIBRATED)
            and self.total_resolved >= 100
            and self.calibration_error < 0.05  # Less than 5% average miscalibration
        )


class BacktestEngine:
    """Engine for running backtests and maintaining calibration data.

    Usage:
        engine = BacktestEngine(db_client)

        # Record a prediction
        engine.record_prediction(
            prediction_id="pred_123",
            market_type="spread",
            sport="NFL",
            predicted_prob=0.58,
            predicted_edge=3.2,
            odds=-110,
        )

        # Later, when outcome is known
        engine.record_outcome("pred_123", won=True, closing_line=-3.5)

        # Get calibration report
        report = engine.get_calibration_report("spread", "NFL")
    """

    def __init__(self, db_client: Any = None):
        """Initialize backtesting engine.

        Args:
            db_client: Database client for persistent storage.
                      If None, uses in-memory storage (for testing).
        """
        self._db = db_client
        self._memory_store: list[BacktestResult] = []  # Fallback for no DB
        self._predictions: dict[str, BacktestResult] = {}  # DB-mode in-memory store

    def record_prediction(
        self,
        prediction_id: str,
        market_type: str,
        sport: str,
        predicted_prob: float,
        predicted_edge: float,
        odds: int,
    ) -> None:
        """Record a model prediction for later evaluation."""
        result = BacktestResult(
            prediction_id=prediction_id,
            timestamp=datetime.now(UTC),
            market_type=market_type,
            sport=sport,
            predicted_probability=predicted_prob,
            predicted_edge=predicted_edge,
            odds=odds,
            outcome=None,
            closing_line=None,
        )

        if self._db:
            self._store_to_db(result)
        else:
            self._memory_store.append(result)

    def record_outcome(
        self,
        prediction_id: str,
        won: bool,
        closing_line: float | None = None,
    ) -> None:
        """Record the outcome of a prediction."""
        if self._db:
            self._update_outcome_db(prediction_id, won, closing_line)
        else:
            for result in self._memory_store:
                if result.prediction_id == prediction_id:
                    result.outcome = won
                    result.closing_line = closing_line
                    break

    def get_calibration_report(
        self,
        market_type: str,
        sport: str | None = None,
        n_bins: int = 10,
    ) -> CalibrationReport:
        """Generate calibration report from historical predictions."""
        # Get resolved predictions
        if self._db:
            results = self._fetch_resolved_predictions(market_type, sport)
        else:
            results = [
                r
                for r in self._memory_store
                if r.outcome is not None
                and r.market_type == market_type
                and (sport is None or r.sport == sport)
            ]

        total_predictions = (
            len(self._memory_store) if not self._db else self._count_predictions(market_type, sport)
        )
        total_resolved = len(results)

        # Determine calibration status
        if total_resolved < 30:
            status = CalibrationStatus.UNCALIBRATED
        elif total_resolved < 100:
            status = CalibrationStatus.PRELIMINARY
        elif total_resolved < 1000:
            status = CalibrationStatus.CALIBRATED
        else:
            status = CalibrationStatus.WELL_CALIBRATED

        # If not enough data, return minimal report
        if total_resolved < 30:
            return CalibrationReport(
                market_type=market_type,
                sport=sport,
                total_predictions=total_predictions,
                total_resolved=total_resolved,
                bins=[],
                brier_score=float("nan"),
                calibration_error=float("nan"),
                discrimination=float("nan"),
                status=status,
                last_updated=datetime.now(UTC),
            )

        # Calculate calibration bins
        probs = np.array([r.predicted_probability for r in results])
        outcomes = np.array([1.0 if r.outcome else 0.0 for r in results])

        bins = self._calculate_calibration_bins(probs, outcomes, n_bins)
        brier_score = self._calculate_brier_score(probs, outcomes)
        calibration_error = self._calculate_calibration_error(bins)
        discrimination = self._calculate_discrimination(probs, outcomes)

        return CalibrationReport(
            market_type=market_type,
            sport=sport,
            total_predictions=total_predictions,
            total_resolved=total_resolved,
            bins=bins,
            brier_score=brier_score,
            calibration_error=calibration_error,
            discrimination=discrimination,
            status=status,
            last_updated=datetime.now(UTC),
        )

    def _calculate_calibration_bins(
        self,
        probs: np.ndarray,
        outcomes: np.ndarray,
        n_bins: int,
    ) -> list[CalibrationBin]:
        """Calculate calibration bins with confidence intervals."""
        bins = []
        bin_edges = np.linspace(0, 1, n_bins + 1)

        for i in range(n_bins):
            mask = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
            if i == n_bins - 1:  # Include right edge in last bin
                mask = (probs >= bin_edges[i]) & (probs <= bin_edges[i + 1])

            n = mask.sum()
            if n == 0:
                continue

            bin_probs = probs[mask]
            bin_outcomes = outcomes[mask]

            predicted_avg = bin_probs.mean()
            actual_rate = bin_outcomes.mean()

            # Wilson score interval for binomial proportion
            ci_lower, ci_upper = self._wilson_score_interval(
                successes=int(bin_outcomes.sum()),
                n=n,
                confidence=0.95,
            )

            std_error = np.sqrt(actual_rate * (1 - actual_rate) / n) if n > 0 else 0

            bins.append(
                CalibrationBin(
                    prob_min=bin_edges[i],
                    prob_max=bin_edges[i + 1],
                    predicted_avg=float(predicted_avg),
                    actual_rate=float(actual_rate),
                    sample_size=int(n),
                    std_error=float(std_error),
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                )
            )

        return bins

    def _wilson_score_interval(
        self,
        successes: int,
        n: int,
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        """Calculate Wilson score confidence interval for a proportion."""
        if n == 0:
            return 0.0, 1.0

        z = stats.norm.ppf(1 - (1 - confidence) / 2)
        p_hat = successes / n

        denominator = 1 + z**2 / n
        center = (p_hat + z**2 / (2 * n)) / denominator
        margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denominator

        return max(0, center - margin), min(1, center + margin)

    def _calculate_brier_score(
        self,
        probs: np.ndarray,
        outcomes: np.ndarray,
    ) -> float:
        """Calculate Brier score (mean squared error of probabilities)."""
        return float(np.mean((probs - outcomes) ** 2))

    def _calculate_calibration_error(self, bins: list[CalibrationBin]) -> float:
        """Calculate mean absolute calibration error."""
        if not bins:
            return float("nan")

        total_samples = sum(b.sample_size for b in bins)
        if total_samples == 0:
            return float("nan")

        weighted_error = sum(b.sample_size * abs(b.predicted_avg - b.actual_rate) for b in bins)
        return weighted_error / total_samples

    def _calculate_discrimination(
        self,
        probs: np.ndarray,
        outcomes: np.ndarray,
    ) -> float:
        """Calculate AUC-ROC for model discrimination ability."""
        from sklearn.metrics import roc_auc_score

        if len(np.unique(outcomes)) < 2:
            return float("nan")

        try:
            return float(roc_auc_score(outcomes, probs))
        except Exception:
            return float("nan")

    # Database methods (in-memory for Phase 1; Phase 4 will wire Supabase)
    def _store_to_db(self, result: BacktestResult) -> None:
        """Store prediction to in-memory dict (Phase 1) / Supabase (Phase 4)."""
        self._predictions[result.prediction_id] = result

    def _update_outcome_db(
        self,
        prediction_id: str,
        won: bool,
        closing_line: float | None,
    ) -> None:
        """Update outcome on stored result (Phase 1) / Supabase row (Phase 4)."""
        if prediction_id in self._predictions:
            stored = self._predictions[prediction_id]
            stored.outcome = won
            stored.closing_line = closing_line

    def _fetch_resolved_predictions(
        self,
        market_type: str,
        sport: str | None,
    ) -> list[BacktestResult]:
        """Fetch resolved predictions from in-memory dict (Phase 1) / Supabase (Phase 4)."""
        return [
            r
            for r in self._predictions.values()
            if r.outcome is not None
            and r.market_type == market_type
            and (sport is None or r.sport == sport)
        ]

    def _count_predictions(self, market_type: str, sport: str | None) -> int:
        """Count total predictions in in-memory dict (Phase 1) / Supabase (Phase 4)."""
        return sum(
            1
            for r in self._predictions.values()
            if r.market_type == market_type and (sport is None or r.sport == sport)
        )


def run_historical_backtest(
    model_predict_fn: Callable[[dict], float],
    historical_games: list[dict],
    market_type: str = "spread",
) -> CalibrationReport:
    """Run a historical backtest on past games.

    Args:
        model_predict_fn: Function that takes game data and returns predicted probability
        historical_games: List of historical games with outcomes
        market_type: Market type being tested

    Returns:
        CalibrationReport from the backtest
    """
    engine = BacktestEngine()  # In-memory for historical backtest

    for i, game in enumerate(historical_games):
        # Generate prediction
        try:
            pred_prob = model_predict_fn(game)
        except Exception as e:
            logger.warning(f"Prediction failed for game {i}: {e}")
            continue

        pred_id = f"backtest_{i}"

        # Record prediction
        engine.record_prediction(
            prediction_id=pred_id,
            market_type=market_type,
            sport=game.get("sport", "unknown"),
            predicted_prob=pred_prob,
            predicted_edge=0,  # Not tracked in simple backtest
            odds=game.get("odds", -110),
        )

        # Record outcome
        outcome = game.get("won")
        if outcome is not None:
            engine.record_outcome(
                prediction_id=pred_id,
                won=outcome,
                closing_line=game.get("closing_line"),
            )

    return engine.get_calibration_report(market_type)
