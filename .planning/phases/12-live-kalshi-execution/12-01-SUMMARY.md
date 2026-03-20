---
phase: 12-live-kalshi-execution
plan: 01
subsystem: testing
tags: [kalshi, tdd, execution-engine, live-trading, settlement-ledger, async]

# Dependency graph
requires:
  - phase: 11-shadow-execution-engine
    provides: ShadowExecutionEngine, OrderIntent, ShadowLedgerEntry, exposure guards
  - phase: 06-settlement-ledger
    provides: SettlementLedger, LedgerEntry with FILL/ADJUSTMENT/POSITION_OPENED event types
provides:
  - KalshiClient.get_order(order_id) async method with 404->None logic
  - 7 RED TDD test stubs defining live execution contracts (EXEC-03, EXEC-05)
  - London School TDD interface contracts for Plan 02 to implement against
affects: [12-02-live-execution-implementation, 13-ablation-validation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "London School TDD: RED stubs written in final GREEN assertion form so Plan 02 requires zero test changes"
    - "Uniform async process_intent: all test calls use await even for shadow mode (Plan 02 makes it uniformly async)"
    - "poll_interval_seconds=0.0 constructor parameter for test-speed polling without real sleep"
    - "KalshiClient.get_order follows get_market() pattern: _auth_headers(GET, path) + _parse_order(data['order'])"

key-files:
  created:
    - packages/venue_adapters/tests/test_live_execution_engine.py
  modified:
    - packages/data_feeds/src/sharpedge_feeds/kalshi_client.py

key-decisions:
  - "get_order placed after get_open_orders() and before create_order() to maintain portfolio methods grouping"
  - "All 7 test calls use await process_intent uniformly — Plan 02 makes process_intent always async; this avoids test file changes post-implementation"
  - "RED failures are TypeError not ImportError — all imports (KalshiOrder, LedgerEntry, SettlementLedger) succeed; only ShadowExecutionEngine constructor kwargs are missing"
  - "make_mock_client(status) fixture pre-wires create_order.return_value=KalshiOrder(status=resting) and get_order.return_value=KalshiOrder(status=param) for clean test setup"

patterns-established:
  - "Phase 12 live tests: inject mock_client + settlement_ledger via constructor; assert entries via ledger.get_position_entries(result.position_lot_id)"
  - "FILL entry: price_at_event = yes_price/100 (cents to probability); notes contain filled qty=N"
  - "ADJUSTMENT entry: amount_usdc > 0 (positive = capital returned); notes contain canceled"
  - "POSITION_OPENED entry: notes contain order_id from create_order response"
  - "position_lot_id is UUID shared across POSITION_OPENED + FILL for the same lot"

requirements-completed: [EXEC-03, EXEC-05]

# Metrics
duration: 8min
completed: 2026-03-20
---

# Phase 12 Plan 01: Live Kalshi Execution TDD Setup Summary

**KalshiClient gains get_order(order_id)->KalshiOrder|None and 7 RED London School test stubs define the full live-mode CLOB execution + fill/cancel polling contracts for EXEC-03 and EXEC-05.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-20T23:40:00Z
- **Completed:** 2026-03-20T23:48:43Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added `get_order(order_id)` async method to KalshiClient — GET /trade-api/v2/portfolio/orders/{id}, returns None on 404
- Created `test_live_execution_engine.py` with 7 failing RED stubs covering: order placement, shadow-mode stability, exposure guard enforcement, fill tracking, cancel tracking, first-poll efficiency, and full end-to-end flow
- All 10 Phase 11 shadow engine tests remain GREEN after additions

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_order() to KalshiClient** - `270cb7c` (feat)
2. **Task 2: Write RED test stubs for EXEC-03 and EXEC-05** - `edf71c4` (test)

## Files Created/Modified
- `packages/data_feeds/src/sharpedge_feeds/kalshi_client.py` - Added `get_order()` async method after `get_open_orders()`, before `create_order()`
- `packages/venue_adapters/tests/test_live_execution_engine.py` - 7 RED TDD contracts for live execution (EXEC-03, EXEC-05)

## Decisions Made
- All process_intent calls use `await` uniformly in tests (even shadow mode) — Plan 02 makes process_intent always async, so no test file changes will be needed after implementation
- `make_mock_client(status)` fixture pattern pre-wires `create_order` and `get_order` returns for each test scenario
- `poll_interval_seconds=0.0` will be a constructor param in Plan 02 to eliminate sleep in tests
- RED failures are `TypeError` (unexpected kwargs), not `ImportError` — confirms all type imports resolve correctly

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 02 (12-02) implements: extends `ShadowExecutionEngine.__init__` with `kalshi_client`, `settlement_ledger`, `poll_interval_seconds`; makes `process_intent` uniformly async; implements `LiveOrderPoller` for fill/cancel tracking
- All 7 test functions are written in final GREEN assertion form — Plan 02 must NOT modify the test file
- `get_order()` is immediately available for the poll loop implementation in Plan 02

---
*Phase: 12-live-kalshi-execution*
*Completed: 2026-03-20*
