"""Prediction Market Resolution Predictor.

ENABLE_PM_RESOLUTION_MODEL-gated inference class that loads per-category
joblib model artifacts and returns ML-predicted resolution probabilities.

When the flag is off or a model file is missing, returns {} so that
scan_pm_edges() falls back to the fee-adjusted implied probability.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import joblib

from sharpedge_models.pm_feature_assembler import PMFeatureAssembler

if TYPE_CHECKING:
    import numpy as np

# Environment flag that enables the ML resolution model.
ENABLE_FLAG = "ENABLE_PM_RESOLUTION_MODEL"

# Directory where per-category joblib model artifacts are stored.
PM_MODEL_DIR = Path("data/models/pm")


class PMResolutionPredictor:
    """Loads per-category ML models and returns market-level probabilities.

    Usage::

        predictor = PMResolutionPredictor()
        model_probs = predictor.build_model_probs(markets)
        edges = scan_pm_edges(..., model_probs=model_probs)

    When ENABLE_PM_RESOLUTION_MODEL is unset or not "true"/"1",
    build_model_probs() returns {} immediately without touching the filesystem.
    """

    def __init__(
        self,
        model_dir: Path | None = None,
        assembler: PMFeatureAssembler | None = None,
    ) -> None:
        self._model_dir: Path = Path(model_dir) if model_dir is not None else PM_MODEL_DIR
        self._assembler: PMFeatureAssembler = (
            assembler if assembler is not None else PMFeatureAssembler()
        )
        # Lazy-loaded cache: category -> model | None
        self._models: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_enabled(self) -> bool:
        """Return True only when ENABLE_PM_RESOLUTION_MODEL is 'true' or '1'."""
        return os.environ.get(ENABLE_FLAG, "").lower() in ("true", "1")

    def _load_model(self, category: str) -> Any | None:
        """Load category model from disk; return None on any error or missing file.

        Never raises. Missing file (FileNotFoundError) is caught by the
        broad except — callers receive None either way.
        """
        model_path = self._model_dir / f"{category}.joblib"
        try:
            return joblib.load(model_path)
        except Exception:
            return None

    def _predict_market(self, market: dict, model: Any) -> float | None:
        """Assemble features and call predict_proba; return None on any error.

        Returns probability of YES (positive class, index 1).
        Never raises.
        """
        try:
            features: np.ndarray = self._assembler.assemble(market)
            proba = model.predict_proba(features.reshape(1, -1))
            return float(proba[0][1])
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_model_probs(self, markets: list[dict]) -> dict[str, float]:
        """Return ML-predicted probabilities keyed by market_id.

        When the feature flag is off or no model artifacts exist, returns
        an empty dict so scan_pm_edges() falls back to fee-adjusted
        implied probability for missing market IDs.

        Args:
            markets: List of market dicts from Kalshi or Polymarket adapters.

        Returns:
            dict[str, float]: market_id -> probability in (0, 1).
                              Empty dict is the correct safe default.
        """
        if not self._is_enabled():
            return {}

        result: dict[str, float] = {}

        for market in markets:
            category = self._assembler.detect_category(market)

            if category not in self._models:
                self._models[category] = self._load_model(category)

            model = self._models[category]
            if model is None:
                continue  # missing model → scanner uses fee-adjusted fallback

            market_id = (
                market.get("ticker") or market.get("condition_id") or market.get("market_id")
            )
            if not market_id:
                continue

            prob = self._predict_market(market, model)
            if prob is not None:
                result[market_id] = prob

        return result
