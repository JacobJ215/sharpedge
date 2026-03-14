---
phase: 01-quant-engine
plan: 01
subsystem: testing
tags: [python, pytest, datetime, visualizations, matplotlib, backtesting, tdd]

requires: []
provides:
  - "timezone-aware datetime.now(timezone.utc) throughout packages/models"
  - "visualizations sub-package with 4 modules and backward-compatible re-exports"
  - "4 BacktestEngine stub methods with in-memory dict implementations"
  - "7 test stub files in RED state (ImportError on modules not yet written)"
  - "tests/conftest.py with shared fixtures"
  - "pytest infrastructure: tests/__init__.py, tests/unit/**/__init__.py"
affects:
  - "02-alpha-composer"
  - "02-monte-carlo"
  - "02-walk-forward"
  - "02-regime-classifier"
  - "02-clv"

tech-stack:
  added: [pytest, sklearn.metrics.roc_auc_score]
  patterns:
    - "TDD RED-GREEN: test stubs written before modules, committed separately"
    - "Sub-package split: flat .py file replaced by directory with __init__.py re-exports"
    - "In-memory dict storage for Phase 1 DB stubs (keyed by prediction_id)"
    - "datetime.now(timezone.utc) throughout — never datetime.utcnow()"

key-files:
  created:
    - packages/analytics/src/sharpedge_analytics/visualizations/__init__.py
    - packages/analytics/src/sharpedge_analytics/visualizations/_helpers.py
    - packages/analytics/src/sharpedge_analytics/visualizations/line_charts.py
    - packages/analytics/src/sharpedge_analytics/visualizations/ev_charts.py
    - packages/analytics/src/sharpedge_analytics/visualizations/public_charts.py
    - tests/__init__.py
    - tests/unit/__init__.py
    - tests/unit/models/__init__.py
    - tests/unit/analytics/__init__.py
    - tests/conftest.py
    - tests/unit/models/test_alpha.py
    - tests/unit/models/test_monte_carlo.py
    - tests/unit/models/test_regime.py
    - tests/unit/analytics/test_key_numbers.py
    - tests/unit/models/test_walk_forward.py
    - tests/unit/models/test_clv.py
    - tests/unit/models/test_backtesting.py
  modified:
    - packages/models/src/sharpedge_models/backtesting.py
    - packages/models/src/sharpedge_models/arbitrage.py
    - packages/models/src/sharpedge_models/ml_inference.py
    - pyproject.toml
    - apps/bot/pyproject.toml
    - packages/analytics/pyproject.toml
    - packages/data_feeds/pyproject.toml

key-decisions:
  - "BacktestEngine DB stubs use in-memory dict (self._predictions) for Phase 1; Supabase wired in Phase 4"
  - "roc_auc_score from sklearn replaces O(n^2) manual concordant-pair loop in _calculate_discrimination"
  - "visualizations split into 4 files: _helpers.py + line_charts.py + ev_charts.py + public_charts.py"
  - "Flutter mobile app excluded from Python workspace (apps/mobile has no pyproject.toml)"
  - "uv workspace requires explicit [tool.uv.sources] in each package that depends on workspace siblings"

patterns-established:
  - "Test stubs: write failing import test first, commit as test(), then implement and commit as feat()"
  - "Sub-package re-export: all public names in __init__.py to preserve caller import paths"
  - "Workspace fix pattern: add [tool.uv.sources] to packages missing workspace sibling entries"

requirements-completed:
  - QUANT-02
  - QUANT-05

duration: 47min
completed: 2026-03-14
---

# Phase 1 Plan 01: Technical Debt Clearance Summary

**Timezone-aware datetime across 7 call sites, visualizations.py (896 lines) split into 4-module sub-package with backward-compat re-exports, 4 BacktestEngine stubs implemented with in-memory dict, and 7 RED test stub files establishing the Wave 1 TDD baseline**

## Performance

- **Duration:** ~47 min
- **Started:** 2026-03-14T00:16:30Z
- **Completed:** 2026-03-14T01:03:00Z
- **Tasks:** 2
- **Files modified:** 17 (created 17, modified 7, deleted 1)

## Accomplishments

- All 7 `datetime.utcnow()` calls replaced with `datetime.now(timezone.utc)` in backtesting.py, arbitrage.py, ml_inference.py
- `visualizations.py` (896 lines) deleted and replaced by `visualizations/` sub-package with 4 modules; all 9 public functions re-exported from `__init__.py` preserving backward compatibility
- 4 `BacktestEngine` stub methods (`_store_to_db`, `_update_outcome_db`, `_fetch_resolved_predictions`, `_count_predictions`) implemented using in-memory dict; all 5 backtesting tests green
- O(n^2) manual AUC-ROC replaced with `sklearn.metrics.roc_auc_score`
- 7 test stub files created in RED state (ImportError on modules not yet written) for QUANT-01 through QUANT-06

## Task Commits

Each task was committed atomically:

1. **RED: test infrastructure + failing backtesting tests** - `653bc5d` (test)
2. **GREEN: datetime fix + backtesting stub implementations** - `67f5c30` (feat)
3. **Task 2: visualizations split + 6 test stub files** - `3174bcb` (feat)

## Files Created/Modified

- `packages/models/src/sharpedge_models/backtesting.py` - timezone fix (3 sites), _predictions dict, 4 stub implementations, roc_auc_score
- `packages/models/src/sharpedge_models/arbitrage.py` - timezone fix (2 field defaults)
- `packages/models/src/sharpedge_models/ml_inference.py` - timezone fix (2 sites)
- `packages/analytics/src/sharpedge_analytics/visualizations/__init__.py` - backward-compat re-exports
- `packages/analytics/src/sharpedge_analytics/visualizations/_helpers.py` - setup_discord_style, fig_to_png_bytes, fig_to_base64, add_watermark, add_gradient_fill
- `packages/analytics/src/sharpedge_analytics/visualizations/line_charts.py` - 4 chart functions
- `packages/analytics/src/sharpedge_analytics/visualizations/ev_charts.py` - 2 chart functions
- `packages/analytics/src/sharpedge_analytics/visualizations/public_charts.py` - 1 chart function
- `tests/conftest.py` - sample_ev_calc and sample_game_inputs fixtures
- `tests/unit/models/test_backtesting.py` - 5 green tests
- `tests/unit/models/test_alpha.py` - 3 RED stubs (QUANT-01)
- `tests/unit/models/test_monte_carlo.py` - 3 RED stubs (QUANT-02)
- `tests/unit/models/test_regime.py` - 4 RED stubs (QUANT-03)
- `tests/unit/analytics/test_key_numbers.py` - 3 RED stubs (QUANT-04)
- `tests/unit/models/test_walk_forward.py` - 3 RED stubs (QUANT-05)
- `tests/unit/models/test_clv.py` - 3 RED stubs (QUANT-06)

## Decisions Made

- BacktestEngine DB methods use in-memory dict (`self._predictions`) for Phase 1; Supabase wiring deferred to Phase 4
- `roc_auc_score` from sklearn replaces O(n^2) list comprehension in `_calculate_discrimination`
- visualizations split grouping: line/bar charts together in `line_charts.py`, EV/CLV in `ev_charts.py`, public betting standalone in `public_charts.py`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stray backtick in apps/bot/pyproject.toml**
- **Found during:** Task 1 (setting up test infrastructure)
- **Issue:** Line 1 had `` ` `` prefix before `[project]`, causing TOML parse error that blocked `uv run`
- **Fix:** Removed the backtick character
- **Files modified:** `apps/bot/pyproject.toml`
- **Verification:** `uv run` no longer reports parse error for this file
- **Committed in:** `653bc5d`

**2. [Rule 3 - Blocking] Added missing [tool.uv.sources] to packages/analytics/pyproject.toml**
- **Found during:** Task 1 (first `uv run` attempt)
- **Issue:** `sharpedge-analytics` listed `sharpedge-shared` as a dependency but had no `[tool.uv.sources]` section, causing uv workspace resolution to fail
- **Fix:** Added `[tool.uv.sources]` with `sharpedge-shared = { workspace = true }`
- **Files modified:** `packages/analytics/pyproject.toml`
- **Verification:** `uv sync --all-packages` succeeds
- **Committed in:** `653bc5d`

**3. [Rule 3 - Blocking] Added missing [tool.uv.sources] to packages/data_feeds/pyproject.toml**
- **Found during:** Task 1 (second `uv run` attempt after analytics fix)
- **Issue:** Same issue as analytics package — `sharpedge-feeds` missing workspace sources for both `sharpedge-shared` and `sharpedge-analytics`
- **Fix:** Added `[tool.uv.sources]` with both workspace entries
- **Files modified:** `packages/data_feeds/pyproject.toml`
- **Verification:** `uv sync --all-packages` succeeds
- **Committed in:** `653bc5d`

**4. [Rule 3 - Blocking] Excluded Flutter mobile app from Python uv workspace**
- **Found during:** Task 1 (third `uv run` attempt)
- **Issue:** `pyproject.toml` workspace glob `apps/*` matched `apps/mobile` which is a Flutter project with no `pyproject.toml`, causing uv to error
- **Fix:** Changed workspace members from `["apps/*", "packages/*"]` to `["apps/bot", "apps/webhook_server", "packages/*"]`
- **Files modified:** `pyproject.toml`
- **Verification:** `uv sync --all-packages` and `uv run pytest` work
- **Committed in:** `653bc5d`

---

**Total deviations:** 4 auto-fixed (1 bug, 3 blocking)
**Impact on plan:** All four fixes were necessary to make `uv run pytest` function at all. No scope creep.

## Issues Encountered

- `uv` binary not on PATH at execution start; installed via `pip install uv` (one-time setup)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Test infrastructure in place; `uv run pytest tests/` works
- 7 RED test stubs define exact signatures for Wave 1 modules (alpha, monte_carlo, regime, key_numbers, walk_forward, clv)
- backtesting.py ready to be used by WalkForwardBacktester (no longer returns [] from stubs)
- All callers of `sharpedge_analytics.visualizations` continue to work unchanged

---
*Phase: 01-quant-engine*
*Completed: 2026-03-14*

## Self-Check: PASSED

All files and commits verified present.
