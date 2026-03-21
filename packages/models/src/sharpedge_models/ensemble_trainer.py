"""Ensemble trainer — 5-model stacking ensemble with LogisticRegression meta-learner.

Trains domain-specific GradientBoostingClassifiers using Out-Of-Fold (OOF)
predictions with TimeSeriesSplit. No data leakage: each base model's
OOF predictions are generated via cross_val_predict, then the meta-learner
is fit only on OOF predictions, never on training-set predictions.

Usage:
    from sharpedge_models.ensemble_trainer import EnsembleManager, train_ensemble

    manager = EnsembleManager()
    manager.train(X_by_domain, y)
    result = manager.predict_ensemble(game_features)
    # {"meta_prob": 0.62, "form_prob": 0.58, "matchup_prob": 0.65, ...}
"""

import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from sharpedge_models.ml_inference import GameFeatures

logger = logging.getLogger(__name__)

# Default model storage location (relative to package root)
DEFAULT_MODELS_DIR = Path(__file__).parent.parent.parent.parent.parent / "data" / "models"

# Domain names (order must match column indices in OOF matrix)
DOMAIN_NAMES = ["form", "matchup", "injury", "sentiment", "weather"]

# DOMAIN_FEATURES: maps domain name to list of GameFeatures attribute names.
# Used when training from a pd.DataFrame and for inference against GameFeatures.
DOMAIN_FEATURES: dict[str, list[str]] = {
    "form": [
        "home_ppg_10g",
        "home_papg_10g",
        "away_ppg_10g",
        "away_papg_10g",
        "home_ats_10g",
        "away_ats_10g",
    ],
    "matchup": [
        "h2h_home_cover_rate",
        "h2h_total_games",
        "home_away_split_delta",
        "opponent_strength_home",
        "opponent_strength_away",
    ],
    "injury": [
        "home_injury_impact",
        "away_injury_impact",
    ],
    "sentiment": [
        "line_movement_velocity",
        "public_pct_home",
    ],
    "weather": [
        "weather_impact_score",
        "travel_penalty",
    ],
}


def save_model_versioned(model_bundle: dict, name: str, models_dir: Path) -> None:
    """Save model with active/previous rotation.

    Rotation pattern:
        active_model.joblib  ->  active_model_prev.joblib (if exists)
        new bundle           ->  active_model.joblib

    Args:
        model_bundle: Dict containing base_models, meta_learner, metadata.
        name: Model name prefix (e.g. "ensemble").
        models_dir: Directory to write model files.
    """
    import joblib

    models_dir.mkdir(parents=True, exist_ok=True)
    active_path = models_dir / f"{name}_model.joblib"
    prev_path = models_dir / f"{name}_model_prev.joblib"

    if active_path.exists():
        if prev_path.exists():
            prev_path.unlink()
        active_path.rename(prev_path)

    joblib.dump(model_bundle, active_path)
    logger.info("Saved %s model to %s", name, active_path)


class EnsembleManager:
    """Domain-separated 5-model stacking ensemble.

    Base models: one GradientBoostingClassifier per domain.
    Meta-learner: LogisticRegression fit on OOF base-model predictions.

    Training accepts either:
    - X_by_domain: dict[str, np.ndarray] — pre-split domain arrays (used in tests)
    - X_df: pd.DataFrame with DOMAIN_FEATURES columns (used in production scripts)

    Both paths produce the same OOF → meta-learner flow.
    """

    def __init__(
        self,
        models_dir: Path | None = None,
        n_splits: int = 5,
    ) -> None:
        self.models_dir = models_dir or DEFAULT_MODELS_DIR
        self.n_splits = n_splits

        # Set after train()
        self._base_models: dict[str, object] = {}
        self._meta_learner: object | None = None
        self._domain_n_features: dict[str, int] = {}  # feature count per domain
        self.oof_preds_: np.ndarray | None = None  # shape (n, 5)
        self.oof_indices: list[tuple] = []  # list of (train_idx, val_idx)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def train(
        self,
        X_input: dict[str, np.ndarray] | pd.DataFrame,
        y: np.ndarray,
        model_version: str = "",
    ) -> None:
        """Train domain-specific base models and meta-learner.

        Args:
            X_input: Either a dict mapping domain_name -> np.ndarray of shape (n, d),
                     or a pd.DataFrame with DOMAIN_FEATURES columns.
            y: Binary target array of shape (n,).
            model_version: Optional version string stored in the model bundle.
        """
        from sklearn.base import clone
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import TimeSeriesSplit

        X_by_domain = self._resolve_domain_arrays(X_input)

        n_samples = len(y)
        n_domains = len(DOMAIN_NAMES)
        oof_preds = np.zeros((n_samples, n_domains))

        tscv = TimeSeriesSplit(n_splits=self.n_splits)

        # Collect fold indices from the first domain (all domains share same n)
        first_domain_X = X_by_domain[DOMAIN_NAMES[0]]
        self.oof_indices = list(tscv.split(first_domain_X))

        base_model_proto = GradientBoostingClassifier(n_estimators=50, max_depth=3, random_state=42)

        final_base_models: dict[str, object] = {}

        for col_idx, domain_name in enumerate(DOMAIN_NAMES):
            X_domain = X_by_domain[domain_name]
            self._domain_n_features[domain_name] = X_domain.shape[1]

            # Generate OOF predictions via TimeSeriesSplit folds
            for train_idx, val_idx in self.oof_indices:
                fold_model = clone(base_model_proto)
                fold_model.fit(X_domain[train_idx], y[train_idx])
                oof_preds[val_idx, col_idx] = fold_model.predict_proba(X_domain[val_idx])[:, 1]

            # Train FINAL base model on full training data
            final_model = clone(base_model_proto)
            final_model.fit(X_domain, y)
            final_base_models[domain_name] = final_model

        # Fit meta-learner on OOF predictions only (no leakage)
        meta = LogisticRegression(C=1.0, max_iter=500, solver="lbfgs")
        meta.fit(oof_preds, y)

        self._base_models = final_base_models
        self._meta_learner = meta
        self.oof_preds_ = oof_preds

        # Optionally persist model
        if self.models_dir is not None:
            trained_at = model_version or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            bundle = {
                "base_models": final_base_models,
                "meta_learner": meta,
                "domain_features": DOMAIN_FEATURES,
                "domain_n_features": self._domain_n_features,
                "model_version": trained_at,
            }
            try:
                save_model_versioned(bundle, "ensemble", self.models_dir)
            except Exception as exc:
                logger.warning("Could not save ensemble model: %s", exc)

    def predict_ensemble(self, features: GameFeatures) -> dict[str, float] | None:
        """Predict from a GameFeatures instance using the trained ensemble.

        Returns dict with keys: meta_prob, form_prob, matchup_prob,
        injury_prob, sentiment_prob, weather_prob.
        Returns None if not yet trained.
        """
        if self._meta_learner is None or not self._base_models:
            logger.warning("EnsembleManager.predict_ensemble called before train()")
            return None

        domain_probs: dict[str, float] = {}

        for domain_name in DOMAIN_NAMES:
            base_model = self._base_models[domain_name]
            n_features = self._domain_n_features.get(domain_name, 0)

            # Build feature array for this domain
            X_domain = self._features_to_array(features, domain_name, n_features)
            prob = float(base_model.predict_proba(X_domain)[0, 1])
            domain_probs[domain_name] = prob

        # Stack into (1, 5) for meta-learner
        meta_input = np.array([[domain_probs[d] for d in DOMAIN_NAMES]])
        meta_prob = float(self._meta_learner.predict_proba(meta_input)[0, 1])

        return {
            "meta_prob": meta_prob,
            "form_prob": domain_probs["form"],
            "matchup_prob": domain_probs["matchup"],
            "injury_prob": domain_probs["injury"],
            "sentiment_prob": domain_probs["sentiment"],
            "weather_prob": domain_probs["weather"],
        }

    def load_models(self) -> bool:
        """Load ensemble model bundle from models_dir.

        Returns True if loaded successfully, False otherwise.
        """
        import joblib

        model_path = self.models_dir / "ensemble_model.joblib"
        if not model_path.exists():
            logger.debug("Ensemble model file not found: %s", model_path)
            return False

        try:
            bundle = joblib.load(model_path)
            self._base_models = bundle["base_models"]
            self._meta_learner = bundle["meta_learner"]
            self._domain_n_features = bundle.get("domain_n_features", {})
            logger.info("Loaded ensemble model from %s", model_path)
            return True
        except Exception as exc:
            logger.error("Failed to load ensemble model: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_domain_arrays(
        self, X_input: dict[str, np.ndarray] | pd.DataFrame
    ) -> dict[str, np.ndarray]:
        """Convert X_input to dict[domain_name -> np.ndarray]."""
        # Check if it's a dict (test path) or DataFrame (production path)
        if isinstance(X_input, dict):
            return {name: np.asarray(X_input[name]) for name in DOMAIN_NAMES}

        # DataFrame path: extract columns per domain
        if isinstance(X_input, pd.DataFrame):
            result = {}
            for domain_name, cols in DOMAIN_FEATURES.items():
                available = [c for c in cols if c in X_input.columns]
                if not available:
                    # Fill with zeros if domain columns not present
                    result[domain_name] = np.zeros((len(X_input), 1))
                else:
                    result[domain_name] = X_input[available].fillna(0.0).values
            return result

        raise TypeError(
            f"X_input must be dict[str, np.ndarray] or pd.DataFrame, got {type(X_input)}"
        )

    def _features_to_array(
        self, features: GameFeatures, domain_name: str, n_features: int
    ) -> np.ndarray:
        """Build (1, n_features) numpy array for a domain from GameFeatures.

        Uses DOMAIN_FEATURES column names when available, falling back to
        zero-filled arrays when the feature count doesn't match.
        """
        domain_cols = DOMAIN_FEATURES.get(domain_name, [])

        # Build array from named attributes when possible
        if domain_cols:
            vals = []
            for col in domain_cols:
                val = getattr(features, col, None)
                if val is None:
                    val = 0.0
                vals.append(float(val))
            feature_arr = np.array(vals).reshape(1, -1)

            # Pad or truncate to match trained n_features
            if feature_arr.shape[1] < n_features:
                padding = np.zeros((1, n_features - feature_arr.shape[1]))
                feature_arr = np.hstack([feature_arr, padding])
            elif feature_arr.shape[1] > n_features:
                feature_arr = feature_arr[:, :n_features]
            return feature_arr

        # No column mapping: return zeros of correct shape
        return np.zeros((1, max(n_features, 1)))


def train_ensemble(
    X_input: dict[str, np.ndarray] | pd.DataFrame,
    y: np.ndarray,
    models_dir: Path | None = None,
    model_version: str = "",
) -> EnsembleManager:
    """Top-level orchestration function: create manager, train, return manager.

    Args:
        X_input: Domain arrays dict or DataFrame with DOMAIN_FEATURES columns.
        y: Binary target array.
        models_dir: Directory for saving model files (default: DEFAULT_MODELS_DIR).
        model_version: Optional version string for the saved bundle.

    Returns:
        Trained EnsembleManager instance.
    """
    manager = EnsembleManager(models_dir=models_dir)
    manager.train(X_input, y, model_version=model_version)
    return manager
