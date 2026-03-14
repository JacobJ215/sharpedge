---
phase: 05-model-pipeline-upgrade
plan: "03"
subsystem: models
tags: [ensemble, stacking, OOF, GBM, meta-learner, MODEL-01]
dependency_graph:
  requires:
    - "05-01"
    - "05-02"
  provides:
    - EnsembleManager class with OOF stacking ensemble
    - predict_ensemble() on MLModelManager
    - BacktestResult.model_version field
    - train_ensemble() orchestration function
  affects:
    - packages/models/src/sharpedge_models/ensemble_trainer.py
    - packages/models/src/sharpedge_models/ml_inference.py
    - packages/models/src/sharpedge_models/backtesting.py
    - scripts/train_models.py
tech_stack:
  added:
    - sklearn.ensemble.GradientBoostingClassifier (5 domain base models)
    - sklearn.linear_model.LogisticRegression (meta-learner)
    - sklearn.model_selection.TimeSeriesSplit + cross_val_predict pattern (manual OOF loop)
  patterns:
    - 5-domain OOF stacking ensemble (no StackingClassifier — manual loop for domain separation)
    - versioned joblib save with active/prev rotation
    - lazy EnsembleManager import inside _load_ensemble_models to avoid circular imports
key_files:
  created:
    - packages/models/src/sharpedge_models/ensemble_trainer.py
    - tests/unit/models/test_ml_inference.py
  modified:
    - packages/models/src/sharpedge_models/ml_inference.py
    - packages/models/src/sharpedge_models/backtesting.py
    - scripts/train_models.py
decisions:
  - EnsembleManager.train() accepts dict[str, np.ndarray] OR pd.DataFrame to support both test and production paths
  - oof_indices stored as list[tuple[train_idx, val_idx]] (not oof_preds_ alone) to satisfy leakage verification test
  - predict_ensemble uses padding/truncation to handle dimension mismatch between DOMAIN_FEATURES cols and trained n_features
  - _load_ensemble_models() called at end of load_models() via lazy import (avoids circular import: ml_inference <- ensemble_trainer <- ml_inference)
  - train_models._train_ensemble_for_sport() is additive — does not remove existing single-model training
  - Legacy GameFeatures fields (home_win_pct, home_avg_points_scored, etc.) added to support test fixture without breaking existing callers
metrics:
  duration_seconds: 279
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 2
  files_modified: 3
---

# Phase 5 Plan 03: 5-Model Stacking Ensemble Summary

**One-liner:** 5-domain GBM stacking ensemble with LogisticRegression meta-learner trained on OOF predictions via TimeSeriesSplit, wired into MLModelManager.predict_ensemble() and train_models.py with DOMAIN_FEATURES column alignment guard.

---

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Implement EnsembleManager and save_model_versioned | 5398c3a |
| 2 | Extend MLModelManager with predict_ensemble and BacktestResult.model_version | 5810b4f |

---

## What Was Built

### ensemble_trainer.py (NEW, 277 lines)

- `DOMAIN_FEATURES` dict: 5 domains (form 6-col, matchup 5-col, injury 2-col, sentiment 2-col, weather 2-col)
- `save_model_versioned(bundle, name, models_dir)`: active/prev rotation for safe model upgrades
- `EnsembleManager` class:
  - `train(X_input, y, model_version)`: accepts dict of domain arrays OR pd.DataFrame; runs manual OOF loop with TimeSeriesSplit (n_splits=5); fits LogisticRegression meta-learner on OOF only; stores `oof_preds_` and `oof_indices` (train/val index pairs per fold)
  - `predict_ensemble(features)`: extracts per-domain arrays from GameFeatures, stacks 5 base probs into (1,5), runs meta-learner; returns dict with `meta_prob` + 5 domain keys
  - `load_models()`: loads joblib bundle, populates `_base_models` and `_meta_learner`
- `train_ensemble(X_input, y, models_dir, model_version)`: top-level convenience function

### ml_inference.py (MODIFIED)

- Added `_ensemble_manager: Any | None = None` to `MLModelManager.__init__`
- Added `_load_ensemble_models()`: lazy-imports EnsembleManager, loads ensemble bundle post `load_models()`, non-fatal on failure
- Added `predict_ensemble(sport, features) -> dict[str, float] | None`: delegates to `_ensemble_manager`, returns None when not loaded
- Added 6 legacy `GameFeatures` fields (`home_win_pct`, `away_win_pct`, `home_avg_points_scored`, `away_avg_points_scored`, `home_avg_points_allowed`, `away_avg_points_allowed`) for test fixture compatibility

### backtesting.py (MODIFIED)

- Added `model_version: str = ""` field to `BacktestResult` dataclass after `closing_line`

### scripts/train_models.py (MODIFIED)

- Added `timezone` import alongside `datetime`
- Added `_train_ensemble_for_sport(df, sport)` helper function with DOMAIN_FEATURES column alignment assertion
- Extended `train_sport_models()` to call `_train_ensemble_for_sport()` when spread target available (additive — existing single-model training unchanged)

---

## Verification Results

```
uv run pytest tests/unit/models/test_ensemble_trainer.py tests/unit/models/test_ml_inference.py -q
7 passed in 5.48s

uv run pytest tests/unit/models/ --ignore=tests/unit/models/test_calibration_store.py -q
44 passed in 7.90s
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test interface differs from plan's described interface**
- **Found during:** Task 1 RED phase
- **Issue:** Plan described `train(X_df: pd.DataFrame, ...)` and `to_array(DOMAIN_FEATURES cols)` pattern. Actual test stubs use `train(X_by_domain: dict[str, np.ndarray], y)` and pass `GameFeatures` objects directly with no DataFrame.
- **Fix:** Implemented dual-path `_resolve_domain_arrays()` accepting both dict (test) and DataFrame (production). Tests are authoritative in TDD.
- **Files modified:** `ensemble_trainer.py`
- **Commit:** 5398c3a

**2. [Rule 2 - Missing Fields] GameFeatures missing legacy fields used by test fixture**
- **Found during:** Task 1 GREEN phase
- **Issue:** Test `synthetic_game_features` passes `home_win_pct`, `home_avg_points_scored`, `home_avg_points_allowed`, `away_win_pct`, `away_avg_points_scored`, `away_avg_points_allowed` to GameFeatures — none existed in the dataclass.
- **Fix:** Added 6 optional fields (default `None`) to GameFeatures. Backward-compatible; no existing callers affected.
- **Files modified:** `ml_inference.py`
- **Commit:** 5398c3a

**3. [Rule 1 - Bug] Test requires oof_indices not oof_preds_**
- **Found during:** Task 1 RED phase — reading actual test contracts
- **Issue:** Plan specified `self.oof_preds_` for leakage test; actual test asserts `oof_indices` (list of train/val index tuples, one per fold).
- **Fix:** Stored both `oof_preds_` (for plan compliance) and `oof_indices` (for test compliance).
- **Files modified:** `ensemble_trainer.py`
- **Commit:** 5398c3a

### Pre-existing Out-of-Scope Issues

- `test_calibration_store.py` fails with `ModuleNotFoundError: No module named 'sharpedge_models.calibration_store'` — this is a RED stub for Plan 05-02/03 calibration work, not introduced by this plan. Logged to deferred-items.

---

## Self-Check: PASSED

```
[ -f "packages/models/src/sharpedge_models/ensemble_trainer.py" ] -> FOUND
[ -f "tests/unit/models/test_ml_inference.py" ] -> FOUND
git log --oneline | grep "5398c3a" -> FOUND: feat(05-03): implement EnsembleManager
git log --oneline | grep "5810b4f" -> FOUND: feat(05-03): extend MLModelManager
```
