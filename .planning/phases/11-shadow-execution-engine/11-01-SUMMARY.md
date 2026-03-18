---
phase: 11-shadow-execution-engine
plan: 01
subsystem: testing
tags: [python, tdd, execution-engine, shadow-trading, exposure-limits, kalshi]

# Dependency graph
requires:
  - phase: 10-training-pipeline-validation
    provides: training artifacts and calibration scores that inform Kelly fraction inputs

provides:
  - execution_engine.py stub module with 6 exported classes (OrderIntent, ShadowLedgerEntry, ShadowLedger, MarketExposureGuard, DayExposureGuard, ShadowExecutionEngine)
  - 10 failing test stubs (RED) defining the contract for Plan 02 implementation
affects:
  - 11-02-PLAN.md (implements these stubs to turn RED -> GREEN)
  - 12-live-kalshi-execution (depends on ShadowExecutionEngine being wired)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD Wave 0 stub pattern — write all failing tests before any implementation exists
    - frozen dataclass UTC guard pattern — __post_init__ raises ValueError on naive datetime (mirrors ledger.py)
    - NotImplementedError stub pattern — class skeletons importable but method calls fail loudly

key-files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py
    - packages/venue_adapters/tests/test_shadow_execution_engine.py
  modified: []

key-decisions:
  - "3 stub-contract tests pass (instantiation, field access, UTC guard) — correct because those behaviors ARE implemented in the stub by design; 7 tests fail on NotImplementedError covering actual engine logic"
  - "test_shadow_mode_no_kalshi_calls written in final GREEN form (asserts ShadowLedgerEntry returned) so Plan 02 implementation turns it green without test changes"
  - "DayExposureGuard midnight reset test uses patch on sharpedge_venue_adapters.execution_engine.datetime so Plan 02 can implement date-based branching without test file changes"

patterns-established:
  - "Stub pattern: all constructors callable without error; all business-logic methods raise NotImplementedError"
  - "UTC guard pattern: frozen dataclass __post_init__ raises ValueError on naive datetime — matches ledger.py convention"

requirements-completed: [EXEC-01, EXEC-02, EXEC-04]

# Metrics
duration: 8min
completed: 2026-03-18
---

# Phase 11 Plan 01: Shadow Execution Engine Stubs Summary

**execution_engine.py stub module with 6 exported classes and 10 RED test stubs defining the full ShadowExecutionEngine contract for Plan 02 implementation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-18T02:38:05Z
- **Completed:** 2026-03-18T02:46:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Created importable execution_engine.py with 6 stub classes: OrderIntent, ShadowLedgerEntry, ShadowLedger, MarketExposureGuard, DayExposureGuard, ShadowExecutionEngine
- UTC guard on both frozen dataclasses (OrderIntent.created_at and ShadowLedgerEntry.timestamp) fully implemented — matches existing ledger.py convention
- 10 test functions matching VALIDATION.md names written in final GREEN form so Plan 02 needs no test changes
- 7/10 tests FAIL (RED) covering process_intent, per-market guard, per-day guard, ledger write, boundary, and midnight reset
- 3/10 tests PASS verifying stub contract is correctly established (instantiation, field access, UTC ValueError)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write execution_engine.py stub module** - `0c1f8bf` (feat)
2. **Task 2: Write failing test stubs (RED)** - `0c4dbc7` (test)

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` - Stub module; 6 classes exported; constructors work; business-logic methods raise NotImplementedError; UTC guards implemented
- `packages/venue_adapters/tests/test_shadow_execution_engine.py` - 10 failing test stubs covering EXEC-01, EXEC-02, EXEC-04

## Decisions Made

- 3 stub-contract tests intentionally pass: `test_shadow_mode_detection` (instantiation only), `test_ledger_entry_fields` (direct dataclass construction), `test_naive_timestamp_rejected` (UTC guard is a contract, fully implemented per plan spec). This is correct RED state.
- Tests written in final GREEN assertion form to avoid requiring test modifications when Plan 02 implements the engine.
- `test_day_stake_resets_at_midnight` patches `sharpedge_venue_adapters.execution_engine.datetime` so Plan 02 can use `datetime.now()` internally with no test changes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- execution_engine.py is importable and all 6 classes are present
- 10 test stubs are in final GREEN form — Plan 02 only needs to implement the engine logic
- CI will fail loudly on these 7 failing tests until Plan 02 (implementation) lands

---
*Phase: 11-shadow-execution-engine*
*Completed: 2026-03-18*

## Self-Check: PASSED

- FOUND: packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py
- FOUND: packages/venue_adapters/tests/test_shadow_execution_engine.py
- FOUND: .planning/phases/11-shadow-execution-engine/11-01-SUMMARY.md
- FOUND: 0c1f8bf (feat: execution_engine.py stub)
- FOUND: 0c4dbc7 (test: failing test stubs)
