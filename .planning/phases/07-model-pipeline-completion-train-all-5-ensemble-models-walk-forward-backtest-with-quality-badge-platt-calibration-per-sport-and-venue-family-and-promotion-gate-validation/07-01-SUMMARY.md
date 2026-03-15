---
phase: 07-model-pipeline-completion
plan: 01
subsystem: testing
tags: [tdd, pytest, ensemble, calibration, walk-forward, promotion-gate, scheduler]

# Dependency graph
requires:
  - phase: 05-model-pipeline-upgrade
    provides: EnsembleManager, WalkForwardBacktester, CalibrationStore interfaces
  - phase: 06-multi-venue-quant-infrastructure
    provides: SnapshotStore, retrain_scheduler, result_watcher infrastructure
provides:
  - RED TDD stubs locking PIPE-01 train/backtest/calibration/alpha pipeline contracts
  - RED TDD stubs locking GATE-01 promotion gate report JSON schema and pass/fail logic
  - RED TDD stubs locking INT-01 compose_alpha CalibrationStore wiring contract
  - GREEN import fix on retrain_scheduler.py (sharpedge_feeds -> sharpedge_db.client)
  - tests/integration/ directory scaffold with __init__.py
affects:
  - 07-02 through 07-05 (Wave 1-5 implementation waves must make RED stubs GREEN)
  - compose_alpha.py wiring (Wave 4)
  - scripts/generate_promotion_gate.py (Wave 4/5)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy in-function imports for test stubs (avoids module-level ImportError blocking collection)
    - RED stubs use raise NotImplementedError with descriptive message citing wave number
    - Commented-out post-implementation assertions in RED stubs (documentation of future contract)

key-files:
  created:
    - tests/unit/models/test_pipeline_integration.py
    - tests/unit/models/test_promotion_gate.py
    - tests/integration/__init__.py
    - tests/integration/test_alpha_pipeline.py
  modified:
    - apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py

key-decisions:
  - "Lazy in-function imports in test_pipeline_integration.py instead of module-level: avoids ModuleNotFoundError blocking collection when uv run pytest without --package flag"
  - "test_promotion_gate.py uses ImportError catch + re-raise for generate_promotion_gate (module doesn't exist yet): ImportError IS valid RED state per TDD plan"
  - "tests/integration/ directory created alongside tests/unit/ at tests/ root level for INT-01 scope separation"

patterns-established:
  - "Wave 0 contract-locking pattern: write ALL test stubs before implementing anything; downstream waves must not change test signatures"
  - "RED state requires tests to COLLECT (4+/3+/2+ tests) and all FAIL with NotImplementedError or ImportError"

requirements-completed: [PIPE-01, GATE-01, INT-01]

# Metrics
duration: 12min
completed: 2026-03-15
---

# Phase 07 Plan 01: Wave 0 RED TDD Stubs + Scheduler Import Fix Summary

**9 RED stub tests locking PIPE-01/GATE-01/INT-01 pipeline contracts, plus corrected sharpedge_db.client import turning test_retrain_scheduler.py GREEN**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-15T02:42:29Z
- **Completed:** 2026-03-15T02:54:30Z
- **Tasks:** 4 (3 RED stub files + 1 import fix)
- **Files modified:** 5

## Accomplishments

- Created 4 RED stub tests in test_pipeline_integration.py locking train_ensemble/WalkForwardBacktester/CalibrationStore/end-to-end contracts (PIPE-01)
- Created 3 RED stub tests in test_promotion_gate.py locking promotion gate JSON schema with 5 required gate keys and pass/fail logic (GATE-01)
- Created tests/integration/ directory with 2 stub tests locking compose_alpha calibration wiring (INT-01); scheduler import test turns GREEN after fix
- Fixed retrain_scheduler.py line 36: `from sharpedge_feeds.supabase_client import get_supabase_client` -> `from sharpedge_db.client import get_supabase_client`

## Task Commits

Each task was committed atomically:

1. **All tasks (Wave 0 complete)** - `8f92ec7` (test): RED stubs for PIPE-01/GATE-01/INT-01 + retrain_scheduler import fix

**Plan metadata:** (docs commit — following)

_Note: TDD Wave 0 locks contracts via a single commit covering all 4 tasks (3 stub files + 1 fix)_

## Files Created/Modified

- `tests/unit/models/test_pipeline_integration.py` - 4 RED stubs for full pipeline: train->backtest->calibrate->alpha (PIPE-01)
- `tests/unit/models/test_promotion_gate.py` - 3 RED stubs for promotion gate report JSON schema and pass/fail logic (GATE-01)
- `tests/integration/__init__.py` - Package marker for integration test directory
- `tests/integration/test_alpha_pipeline.py` - 1 RED stub for compose_alpha CalibrationStore wiring; 1 GREEN scheduler import test (INT-01)
- `apps/webhook_server/src/sharpedge_webhooks/jobs/retrain_scheduler.py` - Fixed line 36 import path

## Decisions Made

- Lazy in-function imports in test_pipeline_integration.py: module-level `import pandas as pd` caused ModuleNotFoundError at collection time when running without `--package sharpedge-models`; moving imports inside test functions fixes collection while preserving RED failure via NotImplementedError
- test_promotion_gate.py uses try/except ImportError + re-raise for `generate_promotion_gate` import: the module doesn't exist yet, so ImportError is the correct and expected RED state
- tests/integration/ placed at tests/ root level (peer to tests/unit/) rather than inside tests/unit/ to reflect the integration scope of INT-01 (cross-package: agent_pipeline + webhooks)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Moved pandas/numpy imports inside test functions to fix collection-time failure**

- **Found during:** Task 1 (test_pipeline_integration.py)
- **Issue:** Module-level `import pandas as pd` caused `ModuleNotFoundError: No module named 'pandas'` at collection time, resulting in 0 tests collected (ERROR) rather than 4 tests FAILED (RED)
- **Fix:** Moved all pandas/numpy imports inside the test function bodies; the final test `test_pipeline_end_to_end` has no imports at all (only raises NotImplementedError immediately)
- **Files modified:** tests/unit/models/test_pipeline_integration.py
- **Verification:** `uv run --package sharpedge-models pytest tests/unit/models/test_pipeline_integration.py -v` shows 4 collected, 4 FAILED
- **Committed in:** 8f92ec7 (combined task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test module structure)
**Impact on plan:** Fix necessary to satisfy the "4+ tests collected" requirement. No scope creep.

## Issues Encountered

- `uv run pytest` without `--package` flag doesn't include workspace package deps (pandas, numpy, sharpedge_models) in the Python path. Running with `uv run --package sharpedge-models pytest` resolves this. Existing tests in tests/unit/models/ already worked this way (they use numpy but not pandas at module level).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All interface contracts are locked via RED stubs — Wave 1-5 implementation must make them GREEN without changing test signatures
- test_retrain_scheduler.py is GREEN (import fix applied)
- tests/integration/ scaffold ready for additional integration tests in later waves
- Downstream concern: `uv run --package sharpedge-models pytest` required to collect tests needing pandas; CI pipelines should use this invocation pattern

---
*Phase: 07-model-pipeline-completion*
*Completed: 2026-03-15*

## Self-Check: PASSED

- FOUND: tests/unit/models/test_pipeline_integration.py
- FOUND: tests/unit/models/test_promotion_gate.py
- FOUND: tests/integration/__init__.py
- FOUND: tests/integration/test_alpha_pipeline.py
- FOUND: 07-01-SUMMARY.md
- FOUND: commit 8f92ec7 (test(07-01): RED TDD stubs)
