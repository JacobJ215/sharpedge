---
phase: 10-training-pipeline-validation
plan: "03"
subsystem: ml-training
tags: [sklearn, brier-score, calibration, randomforest, joblib, walk-forward, pm-models]

requires:
  - phase: 10-01
    provides: resolved_pm_markets DDL migration and Wave 0 test scaffold
  - phase: 10-02
    provides: download_pm_historical.py and process_pm_historical.py with Supabase upsert

provides:
  - train_pm_models.py with calibration_score (Brier score) in every successful training report entry
  - quality_below_minimum skip entries include calibration_score=None for schema consistency
  - scripts/__init__.py enabling scripts/ to be imported as a Python package in tests
  - All 4 test_train_pm_models.py tests green, including TRAIN-04 calibration_score test

affects:
  - Phase 11 (Shadow Execution Engine)
  - Phase 13 (Ablation Validation and Capital Gate) — training_report.json now includes calibration_score field

tech-stack:
  added: [sklearn.metrics.brier_score_loss]
  patterns: [OOF Brier score computed per-category and written to training report JSON alongside badge and market_count]

key-files:
  created:
    - scripts/__init__.py
  modified:
    - scripts/train_pm_models.py

key-decisions:
  - "brier_score_loss computed from OOF arrays already available in train_category() — no new data pipeline required"
  - "calibration_score guarded with len-match check and try/except to survive edge cases (single-class OOF, empty arrays)"
  - "quality_below_minimum skip entry includes calibration_score=None to keep report schema consistent for downstream consumers"
  - "scripts/__init__.py added as blocking fix — scripts/ was not importable as Python package, breaking all unit/scripts tests"

patterns-established:
  - "Report schema: every train_category() entry (success or skip) includes calibration_score key so consumers can rely on schema without None-checking the key itself"

requirements-completed: [TRAIN-03, TRAIN-04]

duration: 8min
completed: 2026-03-16
---

# Phase 10 Plan 03: Training Pipeline Validation — Calibration Score Summary

**Per-category RandomForest training report enriched with Brier score (calibration_score) computed from OOF predictions, completing TRAIN-04 and turning all 4 test_train_pm_models.py tests green.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-16T01:50:00Z
- **Completed:** 2026-03-16T01:58:16Z
- **Tasks:** 1 (+ 1 checkpoint auto-approved)
- **Files modified:** 2

## Accomplishments

- Added `brier_score_loss` import from `sklearn.metrics` to `train_pm_models.py`
- Compute `calibration_score` (Brier score on OOF data) with length guard and exception handler immediately before the final `_write_entry()` call in `train_category()`
- Successful training report entries now contain `calibration_score: float | None` alongside `badge`, `market_count`, and `model_path`
- `quality_below_minimum` skip entries now include `calibration_score: None` for schema consistency
- Fixed blocking import issue: added `scripts/__init__.py` so all `from scripts.X import Y` statements in unit tests resolve correctly
- All 24 `tests/unit/scripts/` tests pass after the fix

## Task Commits

1. **Task 1: Add calibration_score to train_pm_models.py report entries** - `f2b2a7f` (feat)

## Files Created/Modified

- `scripts/train_pm_models.py` — Added brier_score_loss import, calibration_score computation block, updated both _write_entry calls
- `scripts/__init__.py` — Created to make scripts/ a Python package importable in tests

## Decisions Made

- Brier score is computed from OOF arrays (`oof_probs`, `oof_actuals`) already produced by `_run_walk_forward()` — no additional data pass needed
- Guard condition: `if oof_probs and oof_actuals and len(oof_probs) == len(oof_actuals)` prevents ValueError on empty or mismatched arrays
- Exception handler prevents any sklearn edge-case failure from aborting an otherwise-successful training run
- `calibration_score: None` in `quality_below_minimum` entries keeps the JSON schema consistent for downstream consumers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added scripts/__init__.py to enable package import in tests**
- **Found during:** Task 1 (initial test run)
- **Issue:** `ModuleNotFoundError: No module named 'scripts.train_pm_models'` — scripts/ directory had no `__init__.py`, making it non-importable as a Python package. This blocked ALL tests in `tests/unit/scripts/`.
- **Fix:** Created `scripts/__init__.py` with a single comment line
- **Files modified:** `scripts/__init__.py` (created)
- **Verification:** All 24 unit/scripts tests pass after creation
- **Committed in:** `f2b2a7f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue)
**Impact on plan:** The missing `__init__.py` was a pre-existing structural issue blocking test discovery; creating it was necessary to run any script test.

## Issues Encountered

- System python (`/Users/revph/opt/anaconda3/bin/python`) was used by default pytest call, which did not have `sharpedge_models` installed. Switched to `.venv/bin/python -m pytest` to use the project virtualenv where all workspace packages are installed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 10 training pipeline fully implemented: migration (01) + download/process (02) + train with calibration_score (03)
- `training_report.json` schema is stable: every entry contains `category`, `skipped`, `badge`, `market_count`, `calibration_score`, `model_path`
- Phase 11 (Shadow Execution Engine) can proceed — all training pipeline prerequisites satisfied

## Self-Check: PASSED

All created files verified present. Task commit f2b2a7f confirmed in git history.

---
*Phase: 10-training-pipeline-validation*
*Completed: 2026-03-16*
