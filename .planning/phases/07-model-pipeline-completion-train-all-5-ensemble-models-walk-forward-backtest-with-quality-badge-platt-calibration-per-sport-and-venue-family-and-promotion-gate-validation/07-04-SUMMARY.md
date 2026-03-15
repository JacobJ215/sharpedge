---
phase: 07-model-pipeline-completion
plan: "04"
subsystem: testing
tags: [walk-forward, backtest, sklearn, gbm, quality-badge, max-drawdown, cli]

requires:
  - phase: 07-01
    provides: train_models.py with get_feature_columns and PROCESSED_DIR constants
  - phase: 07-03
    provides: WalkForwardBacktester.run_with_model_inference() in walk_forward.py

provides:
  - scripts/run_walk_forward.py — CLI orchestrator that loads parquet, runs walk-forward, saves JSON report
  - compute_max_drawdown() — cumulative-wealth drawdown from per-window ROI sequence
  - data/walk_forward_{sport}_report.json — machine-readable artifact with quality_badge/roi/max_drawdown/windows
  - 3 tests covering walk-forward badge and drawdown correctness in test_pipeline_integration.py

affects:
  - 07-05 (Platt calibration plan consuming walk-forward badge)
  - 07-06 (promotion gate consuming walk_forward_{sport}_report.json)

tech-stack:
  added: []
  patterns:
    - Thin CLI orchestrator pattern — business logic in packages, script is entry point only
    - Deferred imports in scripts for importlib compatibility (pandas/sklearn loaded inside functions)
    - pytest.importorskip for optional-dependency tests (consistent with test_walk_forward.py)

key-files:
  created:
    - scripts/run_walk_forward.py
  modified:
    - tests/unit/models/test_pipeline_integration.py

key-decisions:
  - "Defer pandas/sklearn imports to function body in run_walk_forward.py so importlib.exec_module succeeds in the root venv without full ML stack"
  - "Use pytest.importorskip('pandas') for test_walk_forward_produces_quality_badge — consistent with existing test_walk_forward.py skip pattern"
  - "compute_max_drawdown uses deferred numpy import so it is importable without pandas/sklearn"
  - "JSON report saved to data/ root (not data/walk_forward_reports/) per plan artifact spec"

patterns-established:
  - "CLI orchestrators in scripts/ must defer heavy imports (pandas, sklearn) to function bodies so they can be loaded via importlib in unit tests"
  - "compute_max_drawdown uses cumulative wealth path: cumprod([1+r]) then peak-to-trough ratio"

requirements-completed: [WALK-01]

duration: 7min
completed: "2026-03-15"
---

# Phase 7 Plan 04: Walk-Forward Backtesting CLI Summary

**CLI orchestrator that runs WalkForwardBacktester.run_with_model_inference() via GBM+StandardScaler pipeline and saves BacktestReport JSON with quality_badge and max_drawdown fields**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-15T02:58:15Z
- **Completed:** 2026-03-15T03:05:43Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Created `scripts/run_walk_forward.py` (179 lines) as a thin CLI orchestrator: `--sport`, `--n-windows`, `--dry-run` flags; exits with code 1 on missing parquet or target column; saves `data/walk_forward_{sport}_report.json`
- Implemented `compute_max_drawdown()` using cumulative wealth path (cumprod) with peak-to-trough drawdown calculation
- Replaced NotImplementedError stub in `test_walk_forward_produces_quality_badge`; added `test_compute_max_drawdown_all_positive` and `test_compute_max_drawdown_with_loss` — both pass GREEN

## Task Commits

1. **Task 1: Create run_walk_forward.py with CLI entry point** - `3c7ec16` (feat)
2. **Task 2: Wire walk forward stub test to pass (GREEN)** - `c5c0031` (test)

## Files Created/Modified

- `scripts/run_walk_forward.py` — CLI orchestrator; loads parquet, calls WalkForwardBacktester.run_with_model_inference(), saves JSON report with quality_badge/overall_roi/max_drawdown/windows
- `tests/unit/models/test_pipeline_integration.py` — replaced stub test; added 2 drawdown tests; updated importlib path resolution to use absolute Path(__file__) resolution

## Decisions Made

- Deferred pandas/sklearn imports to function bodies in `run_walk_forward.py` so the module can be loaded by `importlib.exec_module` in the root venv without the full ML stack. This is the critical pattern that lets `compute_max_drawdown` be tested without installing pandas.
- Used `pytest.importorskip("pandas")` for `test_walk_forward_produces_quality_badge` — consistent with the existing project pattern in `test_walk_forward.py`. The test is skipped (not failed) when pandas is absent from root venv.
- JSON report path is `data/walk_forward_{sport}_report.json` (not `data/walk_forward_reports/`) per plan artifact spec.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deferred module-level pandas/sklearn imports to function bodies**
- **Found during:** Task 2 (test wiring)
- **Issue:** Original `run_walk_forward.py` had `import pandas as pd` at module level; `importlib.exec_module` failed in root venv with `ModuleNotFoundError: No module named 'pandas'`, preventing `compute_max_drawdown` from being imported by tests
- **Fix:** Moved pandas/sklearn imports inside `run_walk_forward()`, `_get_feature_columns()`, `_build_model_fn()`, and `main()` function bodies; compute_max_drawdown uses deferred `import numpy as np`
- **Files modified:** scripts/run_walk_forward.py
- **Verification:** `test_compute_max_drawdown_all_positive` and `test_compute_max_drawdown_with_loss` pass GREEN; `python3 -c "import ast; ast.parse(open('scripts/run_walk_forward.py').read())"` succeeds
- **Committed in:** c5c0031 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug, module-level import incompatibility)
**Impact on plan:** Essential fix for importlib-based test loading. No scope creep.

## Issues Encountered

None beyond the import deferral fix above.

## Next Phase Readiness

- `scripts/run_walk_forward.py` is ready for CLI use once processed parquet exists at `data/processed/{sport}_training.parquet`
- `data/walk_forward_{sport}_report.json` artifact format is defined and ready for consumption by `generate_promotion_gate.py` (Wave 5)
- `compute_max_drawdown` is tested and importable; max_drawdown field is included in report JSON for promotion gate threshold checks

## Self-Check: PASSED

- scripts/run_walk_forward.py: FOUND
- tests/unit/models/test_pipeline_integration.py: FOUND
- Commit 3c7ec16 (Task 1): FOUND
- Commit c5c0031 (Task 2): FOUND

---
*Phase: 07-model-pipeline-completion*
*Completed: 2026-03-15*
