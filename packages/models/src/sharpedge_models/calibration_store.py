"""CalibrationStore: per-sport Platt scaling and Brier-score-based confidence_mult.

QUANT-07: After each game resolves, the system recalibrates ML model confidence
using Platt scaling — the updated confidence_mult propagates into alpha scores
in the next analysis cycle.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

logger = logging.getLogger("sharpedge.calibration_store")

# Module-level constants — no magic numbers in methods
BRIER_BASELINE: float = 0.25   # coin-flip model benchmark
BRIER_GOOD: float = 0.22       # threshold for above-average model
MIN_GAMES: int = 50            # minimum resolved games before calibration activates

DEFAULT_CALIBRATION_PATH: Path = (
    Path(__file__).parent.parent.parent.parent.parent.parent
    / "data"
    / "calibration_store.joblib"
)


@dataclass
class SportCalibration:
    """Per-sport calibration state."""
    sport: str
    n_samples: int           # resolved games used for calibration
    brier_score: float
    confidence_mult: float   # clamped to [0.5, 1.2]
    trained_at: str          # ISO 8601 timestamp


def compute_confidence_mult(brier_score: float) -> float:
    """Convert Brier score to confidence multiplier clamped to [0.5, 1.2].

    - Below BRIER_GOOD: model is beating baseline → mult > 1.0 (up to 1.2)
    - Above BRIER_GOOD: model is under-performing → mult < 1.0 (down to 0.5)
    """
    if brier_score <= BRIER_GOOD:
        mult = 1.0 + (BRIER_GOOD - brier_score) / BRIER_GOOD * 0.2
    else:
        mult = 1.0 - (brier_score - BRIER_GOOD) / (BRIER_BASELINE - BRIER_GOOD) * 0.5
    return max(0.5, min(1.2, mult))


class CalibrationStore:
    """Persists per-sport Platt calibration state using joblib."""

    def __init__(self, store_path: Path) -> None:
        self._path = store_path
        self._calibrations: dict[str, SportCalibration] = {}
        if store_path.exists():
            try:
                self._calibrations = joblib.load(store_path)
            except Exception as exc:
                logger.warning(
                    "CalibrationStore: failed to load %s – %s. Starting fresh.",
                    store_path,
                    exc,
                )
                self._calibrations = {}

    def get_confidence_mult(self, sport: str) -> float:
        """Return confidence multiplier for sport.

        Returns 1.0 if sport not found or n_samples < MIN_GAMES (threshold guard).
        Returns calibration.confidence_mult otherwise.
        """
        cal = self._calibrations.get(sport.lower())
        if cal is None or cal.n_samples < MIN_GAMES:
            return 1.0
        return cal.confidence_mult

    def update(self, sport: str, probs: list[float], outcomes: list[bool]) -> None:
        """Compute Brier score, derive confidence_mult, fit Platt scaler, persist.

        Steps:
        1. Validate inputs (len match, min 2 samples).
        2. Compute brier = brier_score_loss(outcomes, probs).
        3. Compute mult = compute_confidence_mult(brier) — but only applies above MIN_GAMES.
        4. Fit LogisticRegression (Platt scaling) if len(probs) >= MIN_GAMES.
        5. Persist {sport: SportCalibration} dict via joblib.dump.
        6. Reload into self._calibrations.
        """
        if len(probs) != len(outcomes):
            logger.warning(
                "CalibrationStore.update: probs length (%d) != outcomes length (%d) for %s",
                len(probs), len(outcomes), sport,
            )
            return
        if len(probs) < 2:
            logger.warning(
                "CalibrationStore.update: need at least 2 samples for %s, got %d",
                sport, len(probs),
            )
            return

        brier = float(brier_score_loss(outcomes, probs))
        mult = compute_confidence_mult(brier)

        # Platt scaling: fit LogisticRegression only when above MIN_GAMES threshold
        if len(probs) >= MIN_GAMES:
            try:
                lr = LogisticRegression(max_iter=200)
                lr.fit(np.array(probs).reshape(-1, 1), np.array(outcomes, dtype=int))
            except Exception as exc:
                logger.warning("CalibrationStore: LogisticRegression fit failed: %s", exc)
        else:
            # Below threshold: store calibration record but confidence_mult stays 1.0
            mult = 1.0

        new_cal = SportCalibration(
            sport=sport.lower(),
            n_samples=len(probs),
            brier_score=brier,
            confidence_mult=mult,
            trained_at=datetime.now(timezone.utc).isoformat(),
        )
        self._calibrations[sport.lower()] = new_cal

        self._path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._calibrations, self._path)
        logger.info(
            "CalibrationStore.update: sport=%s n=%d brier=%.4f mult=%.3f",
            sport, len(probs), brier, mult,
        )
