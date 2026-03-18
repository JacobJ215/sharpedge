---
phase: 15-arb-scanner-hardening
plan: 01
subsystem: testing
tags: [pytest, asyncio, tdd, arbitrage, prediction-markets, kalshi, polymarket]

# Dependency graph
requires:
  - phase: 15-arb-scanner-hardening
    provides: "15-RESEARCH.md with ARB-01 through ARB-04 behavioral contracts"

provides:
  - "8 failing RED tests locking behavioral contracts for ARB-01 through ARB-04"
  - "packages/analytics/tests/__init__.py — makes tests/ a pytest-discoverable package"
  - "packages/analytics/tests/test_realtime_scanner.py — full RED test suite"

affects:
  - 15-02 (GREEN phase — implements staleness guard and NO-token orderbook fetch)
  - 15-03 (GREEN phase — implements discover_and_wire and shadow_execute_arb)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD RED phase: import guards using try/except with _AVAILABLE flag to fail explicitly via pytest.fail() rather than skip"
    - "_make_scanner() helper passes staleness_threshold_s to lock ARB-03 constructor contract"
    - "_make_pair() helper with explicit timestamp and price params for staleness test clarity"

key-files:
  created:
    - packages/analytics/tests/__init__.py
    - packages/analytics/tests/test_realtime_scanner.py
  modified: []

key-decisions:
  - "ARB-02 RED uses try/except import guard (_SHADOW_EXECUTE_AVAILABLE) and explicit pytest.fail() so test appears as FAILED (not ERROR/skip) in RED phase — makes test counter accurate"
  - "ARB-04 RED: PolymarketCLOBOrderClient import also guarded — test_no_token_real_ask fails via missing scanner attribute, not ImportError, keeping the test count at 8 FAILED"
  - "test_staleness_guard_uninit fails via AssertionError on missing staleness_threshold_s attribute — tests the ARB-03 constructor contract specifically"
  - "All async tests use @pytest.mark.asyncio (pytest-asyncio already in project); no pytest.ini asyncio_mode=auto added to avoid global side effects"

patterns-established:
  - "Pattern 1: import-guard pattern — wrap missing future symbols in try/except with bool flag, fail explicitly via pytest.fail() rather than using importorskip"
  - "Pattern 2: helper factories _make_scanner() and _make_pair() accept **kwargs over defaults for concise per-test setup"

requirements-completed: [ARB-01, ARB-02, ARB-03, ARB-04]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 15 Plan 01: Arb Scanner Hardening Summary

**8 failing RED tests locking ARB-01 through ARB-04 behavioral contracts — staleness guard, NO-token CLOB fetch, auto-discovery, and dual order placement**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T03:08:55Z
- **Completed:** 2026-03-18T03:11:00Z
- **Tasks:** 1 (TDD RED phase)
- **Files modified:** 2

## Accomplishments

- Created `packages/analytics/tests/__init__.py` to make tests/ a pytest-discoverable package
- Wrote 8 failing test stubs in `test_realtime_scanner.py` covering all 4 ARB requirements
- Verified RED state: `8 failed, 0 passed` via `uv run pytest packages/analytics/tests/test_realtime_scanner.py -q`
- No production code modified — pure TDD RED phase

## Task Commits

Each task was committed atomically:

1. **Task 1: TDD RED — 8 failing tests** - `1640999` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `packages/analytics/tests/__init__.py` — empty init making tests/ a Python package
- `packages/analytics/tests/test_realtime_scanner.py` — 8 RED tests: 3x ARB-03, 2x ARB-04, 2x ARB-01, 1x ARB-02

## Decisions Made

- ARB-02 RED uses try/except import guard with `_SHADOW_EXECUTE_AVAILABLE` flag and explicit `pytest.fail()` so the test counts as FAILED (not ERROR) — keeps the 8 FAILED count accurate
- `test_staleness_guard_uninit` fails via `AssertionError` on missing `staleness_threshold_s` attribute — tests the ARB-03 constructor contract; avoids needing a running event loop for the RED assertion
- `@pytest.mark.asyncio` used per-test rather than setting `asyncio_mode=auto` globally to avoid unintended side effects on other packages

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- RED test suite is complete and all 8 tests fail as required
- Plan 02 (GREEN phase) implements ARB-03 staleness guard and ARB-04 NO-token orderbook fetch — tests will turn green after those changes
- Plan 03 (GREEN phase) implements ARB-01 discover_and_wire() and ARB-02 shadow_execute_arb() — remaining tests turn green
- No blockers for Plan 02

## Self-Check: PASSED

- FOUND: packages/analytics/tests/__init__.py
- FOUND: packages/analytics/tests/test_realtime_scanner.py
- FOUND: .planning/phases/15-arb-scanner-hardening/15-01-SUMMARY.md
- FOUND commit: 1640999

---
*Phase: 15-arb-scanner-hardening*
*Completed: 2026-03-18*
