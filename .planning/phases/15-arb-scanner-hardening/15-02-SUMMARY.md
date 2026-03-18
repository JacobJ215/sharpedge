---
phase: 15-arb-scanner-hardening
plan: 02
subsystem: analytics
tags: [prediction-markets, arb-scanner, kalshi, polymarket, staleness-guard, clob-orderbook]

# Dependency graph
requires:
  - phase: 15-01
    provides: RED test suite with 8 failing tests covering ARB-01 through ARB-04

provides:
  - staleness guard in RealtimeArbScanner._check_pair() with staleness_threshold_s parameter
  - get_no_token_best_ask() method on PolymarketClient for CLOB orderbook fetch
  - _poly_client injection point on RealtimeArbScanner for on-demand NO token fetching
affects: [15-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Staleness guard: only fires when both timestamps > 0 — uninitialized pairs (0.0/0.0) fall through to the price>0 guard"
    - "ARB-04 3-priority poly_no_ask derivation: stream > CLOB fallback > 1-yes_ask approximation"
    - "_poly_client injection point pattern: set None by default, injected at wire-time for CLOB access"

key-files:
  created: []
  modified:
    - packages/analytics/src/sharpedge_analytics/prediction_markets/realtime_scanner.py
    - packages/data_feeds/src/sharpedge_feeds/polymarket_client.py
    - packages/analytics/tests/test_realtime_scanner.py

key-decisions:
  - "Scanner calls get_orderbook() directly on _poly_client (not get_no_token_best_ask()) so test mocks on get_orderbook propagate correctly — get_no_token_best_ask() is added to PolymarketClient for external use"
  - "poly_no_ask persisted on pair when CLOB ask found; stays 0.0 on empty orderbook to match test assertion"
  - "test_staleness_guard_uninit RED wrapper (pytest.raises(AssertionError)) replaced with direct positive assertions: hasattr check + await _check_pair + log capture (Rule 1 auto-fix)"

patterns-established:
  - "Staleness guard pattern: guard outer if on both timestamps > 0, inner if per side with logger.warning before return"
  - "CLOB best-ask parse pattern: iterate asks list, min float(level['price']) with try/except, return None on empty"

requirements-completed: [ARB-03, ARB-04]

# Metrics
duration: 18min
completed: 2026-03-17
---

# Phase 15 Plan 02: ARB-03 + ARB-04 GREEN Implementation Summary

**Staleness guard (time.time() age check) and real NO-token CLOB orderbook fetch added to _check_pair(), turning 5 of 8 RED tests GREEN**

## Performance

- **Duration:** 18 min
- **Started:** 2026-03-17T00:00:00Z
- **Completed:** 2026-03-17T00:18:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- ARB-03: `staleness_threshold_s=5.0` parameter added to `RealtimeArbScanner.__init__()` and stored as instance attribute
- ARB-03: Staleness guard inserted in `_check_pair()` — checks `last_kalshi_ts` and `last_poly_ts` age only when both > 0 (uninitialised pairs skip the guard entirely)
- ARB-04: `get_no_token_best_ask(no_token_id)` method added to `PolymarketClient` — fetches CLOB orderbook and returns best ask price or `None`
- ARB-04: `_check_pair()` updated with 3-priority poly_no_ask derivation (stream > CLOB fetch > 1-yes_ask approximation)
- `self._poly_client: object | None = None` injection point added to scanner for CLOB access during evaluation

## Task Commits

1. **Task 1: ARB-03 staleness guard** - `dbdf05c` (feat)
2. **Task 2: ARB-04 NO token CLOB orderbook** - `e8f03da` (feat)

## Files Created/Modified

- `packages/analytics/src/sharpedge_analytics/prediction_markets/realtime_scanner.py` — staleness guard + _poly_client injection + ARB-04 price derivation block
- `packages/data_feeds/src/sharpedge_feeds/polymarket_client.py` — get_no_token_best_ask() method added after get_orderbook()
- `packages/analytics/tests/test_realtime_scanner.py` — test_staleness_guard_uninit RED wrapper replaced with GREEN assertions (Rule 1 auto-fix)

## Decisions Made

- Scanner calls `get_orderbook()` directly on `_poly_client` in `_check_pair()` (not via `get_no_token_best_ask()`) so test mocks on `get_orderbook` take effect through the mock object — `get_no_token_best_ask()` is on `PolymarketClient` for external callers
- `pair.poly_no_ask` is persisted when a CLOB ask is found; left at `0.0` when orderbook is empty (no persistence) — matches `test_no_token_fallback` assertion exactly
- Staleness guard outer condition `if pair.last_kalshi_ts > 0 and pair.last_poly_ts > 0` ensures the guard never fires `now - 0.0 ≈ epoch age` for uninitialized pairs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_staleness_guard_uninit RED-phase wrapper for GREEN pass**
- **Found during:** Task 1 (staleness guard implementation)
- **Issue:** Test wrapped `assert hasattr(scanner, "staleness_threshold_s")` in `pytest.raises(AssertionError)` — this is the RED mechanism (attribute missing → assert fails → pytest.raises catches it). In GREEN, attribute exists → assert passes → no AssertionError raised → pytest.raises fails with `Failed: DID NOT RAISE`
- **Fix:** Removed `pytest.raises(AssertionError)` wrapper; replaced with direct `assert hasattr(...)` + `await scanner._check_pair(pair)` with inline log capture to verify no staleness warning fires for 0.0 timestamps
- **Files modified:** packages/analytics/tests/test_realtime_scanner.py
- **Verification:** All 3 staleness tests pass; test intent (staleness guard doesn't fire on uninit pair) is now actually verified
- **Committed in:** dbdf05c (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test structure preventing GREEN pass)
**Impact on plan:** Fix required for plan success criteria. Actual test intent is preserved and now correctly verified.

## Issues Encountered

None — implementation matched plan specification. The test auto-fix was the only unplanned action.

## Next Phase Readiness

- 5 of 8 tests pass: `test_staleness_guard_kalshi`, `test_staleness_guard_poly`, `test_staleness_guard_uninit`, `test_no_token_real_ask`, `test_no_token_fallback`
- 3 tests remain RED for Plan 03 (ARB-01, ARB-01 extraction, ARB-02): `test_discover_and_wire`, `test_no_token_extraction`, `test_dual_order_placement`
- Plan 03 implements `discover_and_wire()` (ARB-01) and `shadow_execute_arb()` (ARB-02)
- `_poly_client` injection point on scanner is in place for Plan 03 to populate at wire time

---
*Phase: 15-arb-scanner-hardening*
*Completed: 2026-03-17*
