---
phase: 05-model-pipeline-upgrade
plan: 01
subsystem: testing
tags: [tdd, pytest, calibration, ensemble, feature-assembler, red-stubs]

requires:
  - phase: 04-api-layer-front-ends
    provides: compose_alpha node, result_watcher job, BettingAlpha dataclass

provides:
  - RED TDD stubs locking CalibrationStore interface (QUANT-07)
  - RED TDD stubs locking FeatureAssembler + GameFeatures MODEL-02 interface
  - RED TDD stubs locking EnsembleManager interface (MODEL-01)
  - RED stubs for trigger_calibration_update in result_watcher (QUANT-07)
  - RED stubs for start_retrain_scheduler (MODEL-01)
  - RED stubs for compose_alpha CalibrationStore wiring (QUANT-07)
  - tests/unit/jobs package init

affects:
  - 05-02 (GameFeatures MODEL-02 fields + FeatureAssembler)
  - 05-03 (EnsembleManager implementation)
  - 05-04 (CalibrationStore implementation + compose_alpha wiring)
  - 05-05 (trigger_calibration_update + retrain_scheduler)

tech-stack:
  added: []
  patterns:
    - "TDD London School: write failing import stubs before any implementation module exists"
    - "Tests import from non-existent modules — ImportError confirms RED state"
    - "CalibrationStore uses joblib persistence with tmp_path pytest fixture for isolation"
    - "EnsembleManager exposes oof_indices attribute for leakage verification in tests"

key-files:
  created:
    - tests/unit/models/test_calibration_store.py
    - tests/unit/models/test_feature_assembler.py
    - tests/unit/models/test_ensemble_trainer.py
    - tests/unit/jobs/__init__.py
    - tests/unit/jobs/test_result_watcher_calibration.py
    - tests/unit/jobs/test_retrain_scheduler.py
    - tests/unit/agent_pipeline/test_compose_alpha.py
  modified: []

key-decisions:
  - "test_feature_assembler.py imports GameFeatures from sharpedge_models.ml_inference (existing) and FeatureAssembler from sharpedge_models.feature_assembler (new) — separates existing vs new interfaces clearly"
  - "EnsembleManager must expose oof_indices attribute so leakage test can verify fold disjointness without mocking internals"
  - "CalibrationStore tests use tmp_path fixture so no disk cleanup needed between test runs"
  - "SPORT_MEDIANS dict added to ml_inference.py as a pre-existing unstaged change — included in feature_assembler tests to lock imputation contract"

patterns-established:
  - "RED stub pattern: import from not-yet-existing module at module level so collection fails with ImportError"
  - "Calibration tests: use synthetic probs/outcomes lists with known properties (all-wrong = high Brier, well-calibrated = low Brier)"
  - "EnsembleManager fixture: 5 domains x 100 samples with fixed rng seed for deterministic test data"

requirements-completed:
  - QUANT-07
  - MODEL-01
  - MODEL-02

duration: 4min
completed: 2026-03-14
---

# Phase 5 Plan 01: Phase 5 Model Pipeline RED Stubs Summary

**TDD London School RED stubs locking CalibrationStore, FeatureAssembler, and EnsembleManager interface contracts across 7 test files — all failing with ImportError until Wave 1-4 implementations ship.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-14T15:04:41Z
- **Completed:** 2026-03-14T15:08:00Z
- **Tasks:** 1 (RED phase)
- **Files created:** 7

## Accomplishments

- 5 RED stubs for CalibrationStore covering Brier score calibration multiplier in [0.5, 1.2] range (QUANT-07)
- 14 RED stubs for FeatureAssembler + GameFeatures MODEL-02 fields including travel penalty, timezone crossings, and sport-specific median imputation (MODEL-02)
- 4 RED stubs for EnsembleManager covering 5-domain training, predict_ensemble output keys, OOF leakage verification, and model loadability (MODEL-01)
- RED stub for trigger_calibration_update in result_watcher calibration hook (QUANT-07)
- RED stub for start_retrain_scheduler returning running AsyncIOScheduler (MODEL-01)
- RED stub locking compose_alpha CalibrationStore wiring: when mocked to 0.8, confidence_mult must be 0.8 not hardcoded 1.0 (QUANT-07)
- Created tests/unit/jobs/ package

## Task Commits

1. **Task 1: RED stubs for Phase 5 model pipeline** - `1365849` (test)

## Files Created/Modified

- `tests/unit/models/test_calibration_store.py` - 5 RED stubs for CalibrationStore (QUANT-07)
- `tests/unit/models/test_feature_assembler.py` - 14 RED stubs for FeatureAssembler + MODEL-02 GameFeatures fields
- `tests/unit/models/test_ensemble_trainer.py` - 4 RED stubs for EnsembleManager (MODEL-01)
- `tests/unit/jobs/__init__.py` - new package init for jobs tests
- `tests/unit/jobs/test_result_watcher_calibration.py` - RED stub for calibration hook
- `tests/unit/jobs/test_retrain_scheduler.py` - RED stub for retrain scheduler
- `tests/unit/agent_pipeline/test_compose_alpha.py` - RED stub for CalibrationStore wiring

## Decisions Made

- `test_feature_assembler.py` imports `GameFeatures` from `sharpedge_models.ml_inference` (existing module) and `FeatureAssembler` from `sharpedge_models.feature_assembler` (new, not yet implemented). This cleanly separates existing vs. new module interfaces. The linter auto-expanded this file with additional `SPORT_MEDIANS` and `compute_timezone_crossings` tests that match the plan's MODEL-02 spec.
- `EnsembleManager` must expose `oof_indices: list[tuple[train_idx, val_idx]]` attribute so the no-leakage test can verify fold disjointness without inspecting internals.
- `CalibrationStore` tests use `tmp_path` pytest fixture to ensure persistence tests use isolated temp files.

## Deviations from Plan

The linter auto-expanded `test_feature_assembler.py` with 9 additional tests beyond the 6 specified in the plan. These include `compute_timezone_crossings`, `travel_penalty_from_crossings`, `SPORT_MEDIANS` structure, and assembler error handling tests. All are within scope for MODEL-02 requirements and strengthen the interface contracts. The original 6 plan tests are all present plus the expanded stubs.

**Total deviations:** 1 auto-enrichment (linter expanded test_feature_assembler.py with additional MODEL-02 contract tests)
**Impact on plan:** Strictly additive — more test coverage locking the interface. No scope creep.

## Issues Encountered

None — all stubs created and confirmed RED on first run.

## Next Phase Readiness

- All interface contracts locked by failing tests
- Plan 05-02 must implement: `GameFeatures` MODEL-02 fields extension + `FeatureAssembler` + `SPORT_MEDIANS`
- Plan 05-03 must implement: `EnsembleManager` with OOF training + meta-learner
- Plan 05-04 must implement: `CalibrationStore` + wire into `compose_alpha` node
- Plan 05-05 must implement: `trigger_calibration_update` in `result_watcher` + `start_retrain_scheduler`

---
*Phase: 05-model-pipeline-upgrade*
*Completed: 2026-03-14*
