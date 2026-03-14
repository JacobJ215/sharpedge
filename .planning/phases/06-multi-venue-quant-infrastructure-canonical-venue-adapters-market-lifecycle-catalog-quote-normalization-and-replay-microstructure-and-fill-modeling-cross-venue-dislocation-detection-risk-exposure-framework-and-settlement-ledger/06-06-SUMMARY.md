---
phase: 06-multi-venue-quant-infrastructure
plan: "06"
subsystem: risk
tags: [kelly-criterion, drawdown-throttle, exposure-book, settlement-ledger, event-sourcing, supabase, append-only]

requires:
  - phase: 06-05
    provides: dislocation detection (DislocatedMarket, scan_dislocation) completing Wave 4
  - phase: 01-quant-engine
    provides: ev_calculator.calculate_ev, monte_carlo.simulate_bankroll (delegated to by compute_allocation)

provides:
  - ExposureBook: tracks open position exposure by venue and market
  - AllocationDecision: frozen dataclass with all Kelly adjustment factors recorded
  - apply_drawdown_throttle: linear scale-down from 10% to 25% DD, floor 0.25
  - compute_allocation: fractional Kelly with drawdown throttle + venue concentration cap
  - LedgerEntry: immutable financial event record with UTC-aware timestamp enforcement
  - LedgerEventType: 7-event literal type (FILL, FEE, REBATE, SETTLEMENT, ADJUSTMENT, POSITION_OPENED, POSITION_CLOSED)
  - SettlementLedger: append-only ledger, in-memory fallback + optional Supabase persistence
  - replay_position_pnl: deterministic PnL computation by summing entries chronologically

affects:
  - Phase 4 (API layer): risk allocation endpoints can delegate to ExposureBook + compute_allocation
  - Bot commands: settlement reconciliation can use SettlementLedger.replay()
  - Supabase: ledger_entries DDL migration appended to scripts/schema.sql

tech-stack:
  added: []
  patterns:
    - "Frozen dataclass for immutable value objects (AllocationDecision, LedgerEntry)"
    - "Try/except delegation to Phase 1 modules with offline fallback"
    - "Append-only event sourcing for financial state (LedgerEntry)"
    - "UTC-aware timestamp enforcement at dataclass construction (__post_init__ ValueError)"
    - "Venue concentration cap as utilization fraction check, not absolute dollar amount"

key-files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/exposure.py
    - packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py
  modified:
    - packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py
    - scripts/schema.sql

key-decisions:
  - "apply_drawdown_throttle floor is 0.25 (25%), not 0 — preserves signal even at max drawdown"
  - "compute_allocation uses offline Kelly fallback (edge / decimal_odds) when ev_calculator unavailable"
  - "LedgerEntry frozen=True enforces immutability; __post_init__ validates UTC-awareness before object creation completes"
  - "SettlementLedger falls back to in-memory mode when SUPABASE_URL env var absent — safe for all test environments"
  - "ledger_entries DDL uses GENERATED ALWAYS AS IDENTITY (not serial) for PK — standard Postgres identity column"
  - "RLS policy on ledger_entries: INSERT-only via named policy; service_role bypasses for reads"

patterns-established:
  - "Wave 5 completes Phase 6: all 10 test files GREEN, all bounded contexts implemented"

requirements-completed:
  - RISK-01
  - SETTLE-01

duration: 3min
completed: 2026-03-14
---

# Phase 06 Plan 06: Risk/Exposure Framework and Settlement Ledger Summary

**ExposureBook with fractional Kelly + venue concentration cap, append-only SettlementLedger with deterministic PnL replay — completing all 10 Phase 6 bounded contexts**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-14T16:34:30Z
- **Completed:** 2026-03-14T16:37:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- ExposureBook tracks open positions by (venue_id, market_id); venue_utilization() checks concentration cap; compute_allocation delegates Kelly sizing to ev_calculator and ruin probability to monte_carlo
- apply_drawdown_throttle: 1.0 at 0-10% drawdown, linear decline to 0.25 floor at 25%+; enforced by 8 tests
- LedgerEntry frozen dataclass with UTC-aware timestamp enforcement; replay_position_pnl sums chronologically (FILL -100 + FEE -7 + SETTLEMENT +200 = 93.0, deterministic)
- All 57 Phase 6 tests GREEN — all 10 bounded contexts (VENUE-01 through SETTLE-01) complete

## Task Commits

Each task was committed atomically:

1. **Task 1: exposure.py — ExposureBook + fractional Kelly with drawdown throttle** - `bfa6285` (feat)
2. **Task 2: ledger.py + schema.sql + __init__.py** - `84a2102` (feat)

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/exposure.py` - ExposureBook, AllocationDecision, apply_drawdown_throttle, compute_allocation
- `packages/venue_adapters/src/sharpedge_venue_adapters/ledger.py` - LedgerEntry, LedgerEventType, SettlementLedger, replay_position_pnl
- `packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py` - exports all public symbols from exposure.py and ledger.py
- `scripts/schema.sql` - appended Part 7 ledger_entries DDL with GENERATED ALWAYS AS IDENTITY PK, RLS INSERT-only policy, and position/venue indexes

## Decisions Made

- apply_drawdown_throttle floor is 0.25 (not 0) — preserves signal even at peak drawdown
- compute_allocation uses offline Kelly fallback when ev_calculator unavailable (edge / decimal_odds), ensures kelly_half > 0 when edge > 0
- LedgerEntry __post_init__ raises ValueError for naive timestamps before object is stored in memory
- SettlementLedger in-memory fallback when SUPABASE_URL absent — all test environments work without credentials

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**External services require manual configuration** for production Supabase settlement ledger:

- Set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` environment variables
- Run the ledger_entries DDL from `scripts/schema.sql` (Part 7) in Supabase SQL Editor
- Without env vars, SettlementLedger operates in in-memory mode (safe for dev/test)

## Next Phase Readiness

- Phase 6 complete: all 10 venue adapter bounded contexts implemented and tested
- All 57 tests GREEN across the full venue_adapters suite
- ExposureBook and SettlementLedger ready for integration with Phase 4 API routes
- ledger_entries Supabase migration ready to deploy

---
*Phase: 06-multi-venue-quant-infrastructure*
*Completed: 2026-03-14*
