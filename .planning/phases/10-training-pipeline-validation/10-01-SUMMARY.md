---
phase: 10-training-pipeline-validation
plan: 01
subsystem: testing
tags: [supabase, postgresql, migrations, pytest, prediction-markets, kalshi, polymarket]

# Dependency graph
requires:
  - phase: 09-prediction-market-models
    provides: download_pm_historical.py, process_pm_historical.py, train_pm_models.py scripts implemented
provides:
  - resolved_pm_markets DDL migration with UNIQUE(market_id, source) idempotency key
  - Wave 0 test scaffold: 5 RED tests documenting contracts for Plans 02 and 03
  - xfail removal: 6 formerly-xfail tests now GREEN (scripts already implemented in Phase 9)
affects:
  - 10-02 (implements against these RED tests — Supabase upsert, preflight, volume filter)
  - 10-03 (implements calibration_score key in train_category report entry)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "UNIQUE(market_id, source) as upsert idempotency key for cross-platform PM data"
    - "Wave 0 contract tests: write RED tests before implementation so Plans 02/03 implement against a spec"
    - "Service role RLS pattern: ALTER TABLE ... ENABLE ROW LEVEL SECURITY + CREATE POLICY service_role USING (true)"

key-files:
  created:
    - packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql
  modified:
    - tests/unit/scripts/test_download_pm_historical.py
    - tests/unit/scripts/test_process_pm_historical.py
    - tests/unit/scripts/test_train_pm_models.py

key-decisions:
  - "One canonical resolved_pm_markets table with source column — not separate tables per platform — accommodates both Kalshi and Polymarket via UNIQUE(market_id, source)"
  - "resolved_yes as INTEGER NOT NULL (0 or 1) to match both Kalshi result=='yes' normalization and Polymarket's native resolved_yes field"
  - "Wave 0 tests written as regular failing tests (not xfail) so they fail loudly until Plan 02/03 implementations land"

patterns-established:
  - "Migration naming: 006_resolved_pm_markets.sql follows existing sequential convention"
  - "Test categorization: Wave 0 = RED tests (contract spec), xfail removal = GREEN (existing impl)"

requirements-completed: [TRAIN-01, TRAIN-02, TRAIN-03, TRAIN-04]

# Metrics
duration: 6min
completed: 2026-03-16
---

# Phase 10 Plan 01: Training Pipeline Validation — Test Scaffold and DDL Summary

**resolved_pm_markets DDL migration with UNIQUE(market_id, source) plus 5 RED Wave 0 tests locking contracts for Plans 02/03 Supabase upsert, preflight, volume filter, and calibration_score**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-16T01:44:42Z
- **Completed:** 2026-03-16T01:50:51Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created `006_resolved_pm_markets.sql` — canonical table for resolved Kalshi + Polymarket markets, with UNIQUE(market_id, source) idempotency key, per-platform indexes, and RLS using the service_role pattern from migrations 003/004
- Added 3 Wave 0 RED tests to `test_download_pm_historical.py`: Supabase upsert path, preflight auth failure exit, and Polymarket volume filter (all fail until Plan 02 implementation)
- Added 1 Wave 0 RED test to `test_process_pm_historical.py`: main() Supabase SELECT path (fails until Plan 02)
- Added 1 Wave 0 RED test to `test_train_pm_models.py`: calibration_score key in report entry (fails until Plan 03)
- Removed all `@pytest.mark.xfail` decorators from 6 stubs in process/train test files — all 6 now pass GREEN (Phase 9 scripts implemented)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create resolved_pm_markets migration DDL** - `b72e025` (feat)
2. **Task 2: Add Wave 0 test coverage for TRAIN-01 through TRAIN-04** - `cdcb9db` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql` - resolved_pm_markets DDL with UNIQUE(market_id, source), category/source indexes, RLS enabled
- `tests/unit/scripts/test_download_pm_historical.py` - +3 Wave 0 RED tests for Supabase upsert, preflight exit, volume filter
- `tests/unit/scripts/test_process_pm_historical.py` - xfail removed from 3 stubs; +1 RED test for Supabase SELECT in main()
- `tests/unit/scripts/test_train_pm_models.py` - xfail removed from 3 stubs; +1 RED test for calibration_score in report entry

## Decisions Made

- Single `resolved_pm_markets` table with `source` column instead of `kalshi_resolved_markets` + `polymarket_resolved_markets` — UNIQUE(market_id, source) as idempotency key for cross-platform upserts
- `resolved_yes` as `INTEGER NOT NULL` (0 or 1) rather than BOOLEAN — matches both Kalshi result=="yes" normalization and Polymarket's existing integer field
- Wave 0 tests written as regular (non-xfail) failing tests so CI fails loudly until implementation lands in Plans 02/03

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- Tests initially run with system Python 3.8 (Anaconda), which doesn't have project packages on path. Discovery: project uses `uv run pytest` for the venv (Python 3.12). All 13 existing tests pass under uv, 5 new tests are RED as designed.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 02 can now implement Supabase upsert in `backfill_kalshi_resolved`, Kalshi preflight auth check, and Polymarket volume filter — all have corresponding RED tests to go GREEN against
- Plan 03 can implement `calibration_score` key in `train_category()` report entry — has a corresponding RED test
- Migration `006_resolved_pm_markets.sql` must be applied to Supabase before any upsert in Plan 02 can work

## Self-Check: PASSED

- FOUND: packages/database/src/sharpedge_db/migrations/006_resolved_pm_markets.sql
- FOUND: tests/unit/scripts/test_download_pm_historical.py
- FOUND: tests/unit/scripts/test_process_pm_historical.py
- FOUND: tests/unit/scripts/test_train_pm_models.py
- FOUND: .planning/phases/10-training-pipeline-validation/10-01-SUMMARY.md
- FOUND commit b72e025 (feat: migration DDL)
- FOUND commit cdcb9db (test: Wave 0 coverage)

---
*Phase: 10-training-pipeline-validation*
*Completed: 2026-03-16*
