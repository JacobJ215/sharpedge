---
phase: 13-ablation-validation-capital-gate
plan: 02
subsystem: execution
tags: [capital-gate, circuit-breaker, live-execution, kalshi, supabase, approval-workflow]

# Dependency graph
requires:
  - phase: 13-01
    provides: CapitalGate stub with RED test suite locking contracts

provides:
  - Full CapitalGate implementation with all 4 gate conditions (GATE-01 through GATE-04)
  - assert_ready() collecting all failures before raising CapitalGateError
  - record_daily_loss() with UTC-midnight reset and .disabled rename on breach
  - from_env() constructing gate from CAPITAL_GATE_* environment variables
  - ShadowExecutionEngine.from_env() wired to call assert_ready() in live mode only
  - scripts/approve_live.py: operator approval CLI writing live_approval.json

affects:
  - phase 14 (dashboard will surface gate status)
  - any live Kalshi execution path

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CapitalGate collects ALL gate failures before raising — operator sees full picture in one error"
    - "Circuit breaker renames approval file to .disabled preserving audit trail (not deleting)"
    - "GATE-02 counts unique calendar days from shadow_ledger timestamps — not just row count"
    - "CapitalGate import inside ENABLE_KALSHI_EXECUTION block only — shadow mode never touches CapitalGate"
    - "GATE-04 fails when approval file absent (no authorization), not just when .disabled exists"

key-files:
  created:
    - scripts/approve_live.py
  modified:
    - packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py

key-decisions:
  - "GATE-04 fails when neither approval nor .disabled exists (uninitialized = not authorized), ensuring all 4 gates fail in a fresh/unconfigured state"
  - "assert_ready() error message includes gate NAME (e.g. GATE-01:) alongside reason so callers can identify which gates failed"
  - "GATE-02 uses unique calendar day count from timestamps rather than just row count — matches plan intent of 'period coverage'"
  - "create_client() called unconditionally when not None (env vars may be empty in tests with mocked create_client)"

patterns-established:
  - "Capital gate wiring: import inside if-block, call assert_ready() before any KalshiClient construction"
  - "Approval script: check GATE-01/02, block if not met, prompt operator, write gate_snapshot at approval time"

requirements-completed: [GATE-01, GATE-02, GATE-03, GATE-04]

# Metrics
duration: 20min
completed: 2026-03-20
---

# Phase 13 Plan 02: CapitalGate Implementation Summary

**Full 4-condition CapitalGate with circuit breaker, Supabase paper-period check, operator approval workflow, and live-mode wiring in ShadowExecutionEngine — all 16 RED tests turned GREEN**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-20T02:00:00Z
- **Completed:** 2026-03-20T02:20:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- All 16 test_capital_gate.py tests pass — GATE-01 (artifact check), GATE-02 (paper period + metrics), GATE-03 (approval JSON validation + staleness check), GATE-04 (circuit breaker with .disabled rename)
- ShadowExecutionEngine.from_env() calls CapitalGate.from_env().assert_ready() inside live-mode branch — shadow mode is completely unaffected (10 shadow tests still pass)
- scripts/approve_live.py blocks on GATE-01/02 failures, prompts operator, writes live_approval.json with operator name and gate_snapshot for staleness detection

## Task Commits

1. **Task 1: Implement CapitalGate class — all 4 gate conditions** - `05b9ebd` (feat)
2. **Task 2: Wire assert_ready() into from_env() + create approve_live.py** - `8e042e8` (feat)

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/capital_gate.py` - Full CapitalGate implementation replacing all NotImplementedError stubs
- `packages/venue_adapters/src/sharpedge_venue_adapters/execution_engine.py` - Added CapitalGate wiring inside ENABLE_KALSHI_EXECUTION block
- `scripts/approve_live.py` - Operator approval CLI: gate status display, GATE-01/02 pre-check, approval JSON writer

## Decisions Made

- **GATE-04 fails when no approval file exists:** A fresh system with no approval has never been authorized. Failing GATE-04 (not just GATE-03) in this state ensures `assert_ready()` lists all 4 failures — the test spec explicitly requires all 4 gates to appear in the error message for an unconfigured gate.
- **assert_ready() includes gate names in error:** Message format `"GATE-01: reason; GATE-02: reason"` rather than just reasons — callers can programmatically scan for specific gate failures.
- **GATE-02 counts unique calendar days:** Rows queried within the cutoff window are grouped by date prefix (timestamp[:10]) to count distinct days covered, not just row count. This correctly reflects "period coverage" semantics.
- **create_client() called without URL/key validation when patched:** Tests patch `create_client` at the module level so URL/key env vars are irrelevant in tests. Removing the env-var guard before the call allows the patch to propagate cleanly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] GATE-04 logic adjusted to fail on no-approval-file state**

- **Found during:** Task 1 (test_assert_ready_collects_all_failures)
- **Issue:** Plan spec said GATE-04 only fails when `.disabled` exists AND approval absent. With fresh state (neither file), GATE-04 would PASS — but the test explicitly requires all 4 gates in the CapitalGateError message.
- **Fix:** GATE-04 also fails when approval file is entirely absent (no authorization granted). This is consistent with the principle that the circuit breaker guards an authorization state — if there's no authorization, the breaker hasn't been cleared.
- **Files modified:** capital_gate.py
- **Verification:** All 16 tests pass including test_assert_ready_collects_all_failures
- **Committed in:** 05b9ebd

**2. [Rule 1 - Bug] assert_ready() error message includes gate names**

- **Found during:** Task 1 (test_assert_ready_collects_all_failures)
- **Issue:** Original assert_ready() stub joined only `f.reason` values. Test asserts `"GATE-01" in msg` — gate name not in reason strings.
- **Fix:** Changed join to `f"{f.name}: {f.reason}"` per-failure.
- **Files modified:** capital_gate.py
- **Verification:** "GATE-01", "GATE-02", "GATE-03", "GATE-04" all appear in CapitalGateError message
- **Committed in:** 05b9ebd

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs in plan spec interpretation)
**Impact on plan:** Both fixes necessary for correctness against the RED test spec. No scope creep.

## Issues Encountered

None beyond the two spec-interpretation deviations documented above.

## User Setup Required

None — no external service configuration required to run tests. For production use, operators must:
1. Set `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` env vars for GATE-02 paper-period check
2. Run `python scripts/approve_live.py` to write `data/live_approval.json` before enabling `ENABLE_KALSHI_EXECUTION=true`

## Next Phase Readiness

- CapitalGate is fully wired — live Kalshi execution now requires all 4 gates to pass
- Phase 13 Plan 03 (ablation validation) can proceed independently
- Phase 14 (dashboard) can surface gate status via `CapitalGate.from_env().check()`

## Self-Check: PASSED

All files confirmed present. Both task commits verified in git log.

---
*Phase: 13-ablation-validation-capital-gate*
*Completed: 2026-03-20*
