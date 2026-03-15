"""Prediction Market Resolution Predictor — stub for Phase 9 plan 01.

Full implementation in plan 03.
"""

from __future__ import annotations

import os
from pathlib import Path

# Environment flag that enables the ML resolution model.
ENABLE_FLAG = "ENABLE_PM_RESOLUTION_MODEL"

# Directory where per-category joblib model artifacts are stored.
PM_MODEL_DIR = Path("data/models/pm")


class PMResolutionPredictor:
    """Loads per-category ML models and returns market-level probabilities.

    build_model_probs() returns {} as a safe default.
    Full loading logic implemented in plan 03.
    """

    def build_model_probs(self, markets: list[dict]) -> dict[str, float]:
        """Return ML-predicted probabilities keyed by market_id.

        When the feature flag is off or no model artifacts exist,
        returns an empty dict so scan_pm_edges() falls back to
        fee-adjusted implied probability for missing market IDs.

        Returns:
            dict[str, float]: market_id → probability in (0, 1).
                              Empty dict is the correct safe default.
        """
        return {}
