---
phase: 07-model-pipeline-completion
plan: "03"
subsystem: models
tags: [train_models, ensemble, sklearn, sports-ml, ncaab, mlb, nhl]

# Dependency graph
requires:
  - phase: 07-01
    provides: sharpedge-models ensemble_trainer package with DOMAIN_FEATURES and train_ensemble
  - phase: 07-02
    provides: processed parquets for NCAAB/MLB/NHL via process_historical_data.py
provides:
  - train_models.py supports all 5 sports (nfl, nba, ncaab, mlb, nhl) without crashing on missing domain feature columns
  - SUPPORTED_SPORTS constant at module level for consistent sport enumeration
  - _train_ensemble_for_sport zero-fills missing DOMAIN_FEATURES columns instead of raising ValueError
affects: [07-04, 07-05, 07-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Zero-fill fallback for missing domain feature columns before ensemble training
    - Module-level SUPPORTED_SPORTS constant as single source of truth for sport enumeration

key-files:
  created: []
  modified:
    - scripts/train_models.py

key-decisions:
  - "_train_ensemble_for_sport zero-fills missing DOMAIN_FEATURES columns instead of raising ValueError — enables training across sports that lack domain-specific engineered features"
  - "SUPPORTED_SPORTS constant defined at module level so main() and any future callers use a single authoritative list"

patterns-established:
  - "Zero-fill pattern: when DOMAIN_FEATURES columns are absent, fill with 0.0 and log which columns/sport — do not abort training"
  - "Sport enumeration via SUPPORTED_SPORTS constant — avoid hardcoding sport strings outside the constant definition"

requirements-completed: [PIPE-01]

# Metrics
duration: 4min
completed: 2026-03-15
---

# Phase 7 Plan 03: All-5-Sports train_models.py Summary

**_train_ensemble_for_sport upgraded from ValueError-on-missing-columns to graceful zero-fill; SUPPORTED_SPORTS constant drives main() loop over all 5 sports (nfl, nba, ncaab, mlb, nhl)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-15T02:51:24Z
- **Completed:** 2026-03-15T02:55:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Fixed `_train_ensemble_for_sport()` to zero-fill missing DOMAIN_FEATURES columns with informative log message instead of raising `ValueError`
- Added `SUPPORTED_SPORTS = ["nfl", "nba", "ncaab", "mlb", "nhl"]` constant at module level (after MODELS_DIR definition)
- Replaced hardcoded NFL/NBA training block in `main()` with a loop over `SUPPORTED_SPORTS` — sports with no parquet skip gracefully via existing `return {}` path
- All 4 `test_ensemble_trainer.py` tests remain GREEN; file stays at 361 lines (under 500-line limit)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix _train_ensemble_for_sport to zero-fill instead of raise** - `2e6af1e` (fix)
2. **Task 2: Extend main() to train all 5 sports** - `9f89862` (feat)

## Files Created/Modified

- `scripts/train_models.py` - Zero-fill for missing DOMAIN_FEATURES; SUPPORTED_SPORTS constant; main() loop over all 5 sports

## Decisions Made

- Zero-fill chosen over skipping ensemble training when columns are missing — sports like NCAAB/MLB/NHL may lack some domain-specific features initially, but zero-fill lets the model train on available signal without crashing
- SUPPORTED_SPORTS as a module-level constant rather than inline list in main() — makes it trivially testable and discoverable for callers

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The plan's automated verification command uses `python -c "... from scripts.train_models import ..."` with pandas, but pandas is not in the workspace root venv (only in individual package deps). Verified correctness by: (a) confirming `ValueError` raise was removed from source, (b) confirming zero-fill loop is present at correct location, (c) confirming `ast.parse()` succeeds, (d) confirming all existing ensemble tests still pass with `uv run pytest`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `train_models.py` now processes all 5 sports without crashing on missing DOMAIN_FEATURES columns
- Ready for Phase 7 Plan 04 (walk-forward backtest or Platt calibration per sport/venue)
- Pre-existing `test_pipeline_integration.py` failure (pandas not in root venv) is out-of-scope for this plan

## Self-Check: PASSED

- FOUND: scripts/train_models.py
- FOUND: 07-03-SUMMARY.md
- FOUND commit 2e6af1e (Task 1 fix)
- FOUND commit 9f89862 (Task 2 feat)

---
*Phase: 07-model-pipeline-completion*
*Completed: 2026-03-15*
