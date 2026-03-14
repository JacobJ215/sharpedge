"""ML Model Inference Module.

This module provides inference capabilities for trained ML models,
integrating them with the existing prediction pipeline.

Features:
- Load trained models (spread, totals)
- Generate probability predictions
- Calculate confidence intervals
- Compare with no-vig baseline
- Track model performance over time
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Model directory - can be overridden
DEFAULT_MODELS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "models"


@dataclass
class MLPrediction:
    """A prediction from an ML model."""
    sport: str
    market_type: str  # "spread" or "totals"
    probability: float  # P(home covers) or P(over)
    confidence: float  # 0-1, based on model certainty
    calibration_status: str  # "calibrated", "preliminary", "uncalibrated"

    # Comparison to no-vig baseline
    no_vig_prob: float | None = None
    model_edge: float | None = None  # Model prob - no-vig prob

    # Feature importance for this prediction
    top_features: list[tuple[str, float]] | None = None

    # Metadata
    model_version: str = ""
    predicted_at: datetime | None = None


@dataclass
class GameFeatures:
    """Features for a single game prediction."""
    home_team: str
    away_team: str
    sport: str

    # Rolling stats (from recent games)
    home_ppg_5g: float | None = None
    home_papg_5g: float | None = None
    away_ppg_5g: float | None = None
    away_papg_5g: float | None = None

    # ATS performance
    home_ats_10g: float | None = None
    away_ats_10g: float | None = None

    # Situational
    home_rest_days: int | None = None
    away_rest_days: int | None = None

    # Line info
    spread_line: float | None = None
    total_line: float | None = None

    def to_array(self, feature_names: list[str]) -> np.ndarray:
        """Convert to numpy array matching model's expected features."""
        values = []
        for name in feature_names:
            val = getattr(self, name, None)
            if val is None:
                val = 0.0  # Default for missing features
            values.append(float(val))
        return np.array(values).reshape(1, -1)


class MLModelManager:
    """Manages loading and inference for ML models."""

    def __init__(self, models_dir: Path | None = None):
        self.models_dir = models_dir or DEFAULT_MODELS_DIR
        self._models: dict[str, tuple[Any, Any]] = {}
        self._metrics: dict[str, dict] = {}
        self._loaded = False

    def load_models(self) -> bool:
        """Load all available trained models."""
        try:
            import joblib
        except ImportError:
            logger.warning("joblib not installed, ML inference unavailable")
            return False

        if not self.models_dir.exists():
            logger.warning(f"Models directory not found: {self.models_dir}")
            return False

        loaded_any = False
        model_files = list(self.models_dir.glob("*_model.joblib"))

        for model_file in model_files:
            name = model_file.stem.replace("_model", "")
            try:
                model_bundle = joblib.load(model_file)
                self._models[name] = model_bundle

                # Load metrics
                metrics_file = self.models_dir / f"{name}_metrics.json"
                if metrics_file.exists():
                    with open(metrics_file) as f:
                        self._metrics[name] = json.load(f)

                logger.info(f"Loaded model: {name}")
                loaded_any = True

            except Exception as e:
                logger.error(f"Failed to load model {name}: {e}")

        self._loaded = loaded_any
        return loaded_any

    @property
    def is_loaded(self) -> bool:
        """Check if any models are loaded."""
        return self._loaded and len(self._models) > 0

    @property
    def available_models(self) -> list[str]:
        """List available models."""
        return list(self._models.keys())

    def get_model_metrics(self, model_name: str) -> dict | None:
        """Get metrics for a specific model."""
        return self._metrics.get(model_name)

    def predict_spread(
        self,
        sport: str,
        features: GameFeatures,
        no_vig_prob: float | None = None,
    ) -> MLPrediction | None:
        """Predict spread outcome (home team covers).

        Args:
            sport: Sport code (nfl, nba)
            features: Game features
            no_vig_prob: Optional no-vig baseline for comparison

        Returns:
            MLPrediction or None if model not available
        """
        model_name = f"{sport.lower()}_spread"

        if model_name not in self._models:
            logger.debug(f"Model not available: {model_name}")
            return None

        model, scaler = self._models[model_name]
        metrics = self._metrics.get(model_name, {})

        try:
            feature_names = metrics.get("feature_names", [])
            X = features.to_array(feature_names)
            # scaler is None when the model was trained with an embedded
            # Pipeline (scaler runs inside the model); pass raw features.
            if scaler is not None:
                X = scaler.transform(X)

            prob = model.predict_proba(X)[0, 1]

            # Calculate confidence based on distance from 0.5
            confidence = abs(prob - 0.5) * 2

            # Determine calibration status based on training sample size
            n_samples = metrics.get("n_samples", 0)
            if n_samples >= 1000:
                cal_status = "calibrated"
            elif n_samples >= 100:
                cal_status = "preliminary"
            else:
                cal_status = "uncalibrated"

            model_edge = None
            if no_vig_prob is not None:
                model_edge = prob - no_vig_prob

            return MLPrediction(
                sport=sport,
                market_type="spread",
                probability=float(prob),
                confidence=float(confidence),
                calibration_status=cal_status,
                no_vig_prob=no_vig_prob,
                model_edge=model_edge,
                model_version=metrics.get("trained_at", "unknown"),
                predicted_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Prediction error for {model_name}: {e}")
            return None

    def predict_totals(
        self,
        sport: str,
        features: GameFeatures,
        no_vig_prob: float | None = None,
    ) -> MLPrediction | None:
        """Predict totals outcome (over).

        Args:
            sport: Sport code (nfl, nba)
            features: Game features
            no_vig_prob: Optional no-vig baseline for comparison

        Returns:
            MLPrediction or None if model not available
        """
        model_name = f"{sport.lower()}_totals"

        if model_name not in self._models:
            logger.debug(f"Model not available: {model_name}")
            return None

        model, scaler = self._models[model_name]
        metrics = self._metrics.get(model_name, {})

        try:
            feature_names = metrics.get("feature_names", [])
            X = features.to_array(feature_names)
            # scaler is None when the model was trained with an embedded
            # Pipeline (scaler runs inside the model); pass raw features.
            if scaler is not None:
                X = scaler.transform(X)

            prob = model.predict_proba(X)[0, 1]
            confidence = abs(prob - 0.5) * 2

            n_samples = metrics.get("n_samples", 0)
            if n_samples >= 1000:
                cal_status = "calibrated"
            elif n_samples >= 100:
                cal_status = "preliminary"
            else:
                cal_status = "uncalibrated"

            model_edge = None
            if no_vig_prob is not None:
                model_edge = prob - no_vig_prob

            return MLPrediction(
                sport=sport,
                market_type="totals",
                probability=float(prob),
                confidence=float(confidence),
                calibration_status=cal_status,
                no_vig_prob=no_vig_prob,
                model_edge=model_edge,
                model_version=metrics.get("trained_at", "unknown"),
                predicted_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            logger.error(f"Prediction error for {model_name}: {e}")
            return None


# Global model manager instance
_model_manager: MLModelManager | None = None


def get_model_manager(models_dir: Path | None = None) -> MLModelManager:
    """Get or create the global model manager."""
    global _model_manager

    if _model_manager is None:
        _model_manager = MLModelManager(models_dir)
        _model_manager.load_models()

    return _model_manager


def predict_spread_ml(
    sport: str,
    home_team: str,
    away_team: str,
    spread_line: float,
    no_vig_prob: float | None = None,
    **kwargs,
) -> MLPrediction | None:
    """Convenience function for spread predictions.

    Args:
        sport: Sport code
        home_team: Home team name
        away_team: Away team name
        spread_line: Current spread line
        no_vig_prob: Optional no-vig fair probability
        **kwargs: Additional features (home_ppg_5g, etc.)

    Returns:
        MLPrediction or None
    """
    manager = get_model_manager()

    if not manager.is_loaded:
        return None

    features = GameFeatures(
        home_team=home_team,
        away_team=away_team,
        sport=sport,
        spread_line=spread_line,
        **kwargs,
    )

    return manager.predict_spread(sport, features, no_vig_prob)


def predict_totals_ml(
    sport: str,
    home_team: str,
    away_team: str,
    total_line: float,
    no_vig_prob: float | None = None,
    **kwargs,
) -> MLPrediction | None:
    """Convenience function for totals predictions.

    Args:
        sport: Sport code
        home_team: Home team name
        away_team: Away team name
        total_line: Current total line
        no_vig_prob: Optional no-vig fair probability
        **kwargs: Additional features

    Returns:
        MLPrediction or None
    """
    manager = get_model_manager()

    if not manager.is_loaded:
        return None

    features = GameFeatures(
        home_team=home_team,
        away_team=away_team,
        sport=sport,
        total_line=total_line,
        **kwargs,
    )

    return manager.predict_totals(sport, features, no_vig_prob)


def get_prediction_with_comparison(
    sport: str,
    market_type: str,
    home_team: str,
    away_team: str,
    line: float,
    odds_home: int,
    odds_away: int,
    **kwargs,
) -> dict:
    """Get ML prediction with comparison to no-vig baseline.

    This is the main function for getting predictions that compares:
    1. No-vig consensus probability (always available)
    2. ML model probability (when model is available)

    Returns dict with both predictions and recommendation.
    """
    from sharpedge_models.no_vig import calculate_no_vig

    # Calculate no-vig baseline
    no_vig = calculate_no_vig(odds_home, odds_away)
    no_vig_prob = no_vig.fair_prob_side1

    # Get ML prediction if available
    manager = get_model_manager()

    ml_prediction = None
    if manager.is_loaded:
        features = GameFeatures(
            home_team=home_team,
            away_team=away_team,
            sport=sport,
            spread_line=line if market_type == "spread" else None,
            total_line=line if market_type == "totals" else None,
            **kwargs,
        )

        if market_type == "spread":
            ml_prediction = manager.predict_spread(sport, features, no_vig_prob)
        else:
            ml_prediction = manager.predict_totals(sport, features, no_vig_prob)

    return {
        "no_vig": {
            "probability": no_vig_prob,
            "fair_odds": no_vig.fair_odds_side1,
            "vig_percentage": no_vig.vig_percentage,
        },
        "ml_model": {
            "available": ml_prediction is not None,
            "probability": ml_prediction.probability if ml_prediction else None,
            "confidence": ml_prediction.confidence if ml_prediction else None,
            "calibration_status": ml_prediction.calibration_status if ml_prediction else None,
            "model_edge": ml_prediction.model_edge if ml_prediction else None,
        },
        "recommendation": {
            # Use ML if available and well-calibrated, otherwise use no-vig
            "use_model": (
                ml_prediction is not None and
                ml_prediction.calibration_status in ["calibrated", "preliminary"]
            ),
            "probability": (
                ml_prediction.probability if ml_prediction and
                ml_prediction.calibration_status in ["calibrated", "preliminary"]
                else no_vig_prob
            ),
            "source": (
                "ml_model" if ml_prediction and
                ml_prediction.calibration_status in ["calibrated", "preliminary"]
                else "no_vig"
            ),
        },
    }
