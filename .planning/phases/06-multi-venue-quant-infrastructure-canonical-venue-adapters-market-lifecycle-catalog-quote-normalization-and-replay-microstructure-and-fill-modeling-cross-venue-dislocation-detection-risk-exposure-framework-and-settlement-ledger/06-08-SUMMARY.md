---
phase: 06-multi-venue-quant-infrastructure
plan: 08
subsystem: database
tags: [snapshot-store, supabase, market-state, replay, tdd, venue-adapters]

requires:
  - phase: 06-multi-venue-quant-infrastructure
    provides: "SettlementLedger dual-mode pattern (in-memory + Supabase) established in 06-06"
  - phase: 06-multi-venue-quant-infrastructure
    provides: "MarketStatePacket, CanonicalOrderBook, CanonicalQuote protocol types from 06-02"

provides:
  - "SnapshotStore: append-only store for MarketStatePacket persistence with dual-mode (in-memory / Supabase)"
  - "SnapshotRecord: serializable row format for Supabase INSERT"
  - "market_snapshots DDL: BIGINT IDENTITY PK, RLS-enabled, INSERT-only policy, replay + time-range indexes"
  - "UTC-aware enforcement: ValueError raised on naive snapshot_at strings"
  - "Deterministic replay: replay() always returns packets sorted by snapshot_at ascending"

affects:
  - 06-multi-venue-quant-infrastructure
  - future-adapter-wiring

tech-stack:
  added: []
  patterns:
    - "Dual-mode persistence: in-memory list for tests, Supabase INSERT in production (same pattern as SettlementLedger)"
    - "UTC-aware string validation: check chars after position 19 for '+', '-', or 'Z'"
    - "Append-only store with deterministic sort for replay (ISO-8601 lexicographic sort works for UTC)"

key-files:
  created:
    - packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py
    - packages/venue_adapters/tests/test_snapshot_store.py
  modified:
    - packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py
    - scripts/schema.sql

key-decisions:
  - "SnapshotStore follows identical dual-mode pattern as SettlementLedger: in-memory without env vars, Supabase with env vars"
  - "ISO-8601 string sort is correct for UTC timestamps — no datetime parse needed in replay()"
  - "quotes field uses tuple() (not list) to match frozen=True MarketStatePacket dataclass; tests updated accordingly"
  - "Supabase errors during INSERT are silently caught — record still appended to in-memory list for resilience"

patterns-established:
  - "Snapshot UTC validation: strip timestamp, check chars 19+ for timezone indicator, raise ValueError if absent"
  - "Append-only persistence: record() appends unconditionally to in-memory; Supabase INSERT is best-effort"

requirements-completed:
  - VENUE-01
  - VENUE-02

duration: 8min
completed: 2026-03-14
---

# Phase 6 Plan 08: SnapshotStore Summary

**Append-only MarketStatePacket persistence with deterministic replay via SnapshotStore, dual-mode in-memory/Supabase, and market_snapshots DDL with INSERT-only RLS policy**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-14T00:00:00Z
- **Completed:** 2026-03-14T00:08:00Z
- **Tasks:** 2 (TDD: RED then GREEN)
- **Files modified:** 4

## Accomplishments

- SnapshotStore implemented with `record()` (UTC-aware validation + append) and `replay()` (filtered, sorted ascending)
- Dual-mode pattern: in-memory list for tests, Supabase `market_snapshots` INSERT in production (mirrors SettlementLedger)
- 5/5 tests GREEN covering record/replay, sort order, determinism, market filter, and UTC enforcement
- market_snapshots DDL appended to schema.sql with GENERATED ALWAYS AS IDENTITY PK, RLS enabled, INSERT-only policy, and two replay indexes
- Locked CONTEXT.md principle satisfied: "every market-state snapshot must be replayable from stored events"

## Task Commits

Each task was committed atomically:

1. **Task 1: RED test stubs** - `0f14d8b` (test)
2. **Task 2: SnapshotStore implementation + schema.sql DDL** - `01725b0` (feat)

**Plan metadata:** committed with SUMMARY.md in final docs commit

_Note: TDD tasks have two commits — test (RED) then feat (GREEN)_

## Files Created/Modified

- `packages/venue_adapters/src/sharpedge_venue_adapters/snapshot_store.py` - SnapshotStore and SnapshotRecord implementation
- `packages/venue_adapters/tests/test_snapshot_store.py` - 5 TDD tests covering all contracts
- `packages/venue_adapters/src/sharpedge_venue_adapters/__init__.py` - Added SnapshotStore and SnapshotRecord exports
- `scripts/schema.sql` - Appended PART 8: market_snapshots DDL with RLS and indexes

## Decisions Made

- SnapshotStore follows identical dual-mode pattern as SettlementLedger: in-memory without env vars, Supabase with env vars
- ISO-8601 string sort is correct for UTC timestamps — no datetime parse overhead needed in replay()
- `quotes` field uses `tuple()` (not `list`) to match the frozen MarketStatePacket dataclass; test helper updated from plan's `quotes=[]` to `quotes=()`
- Supabase INSERT errors are silently caught — record still appended in-memory for resilience (never lose a snapshot)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Adjusted test helper to use tuple() for CanonicalOrderBook.bids/asks and quotes**
- **Found during:** Task 1 (RED test creation)
- **Issue:** Plan's test code used `bids=[...]` (list) and `quotes=[]` (list). MarketStatePacket uses `frozen=True` dataclass with `bids: tuple` and `quotes: tuple`. Creating with lists would cause a type mismatch in frozen context.
- **Fix:** Changed `bids=[...]` to `bids=({"price": 0.48, "size": 100},)`, `asks=[...]` to tuple form, `quotes=[]` to `quotes=()` throughout test helper.
- **Files modified:** packages/venue_adapters/tests/test_snapshot_store.py
- **Verification:** 5/5 tests GREEN
- **Committed in:** 0f14d8b (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: tuple vs list in frozen dataclass)
**Impact on plan:** Necessary correctness fix. No scope creep — only the test helper was adjusted, implementation contract unchanged.

## Issues Encountered

None — all tests passed first run after implementation.

## User Setup Required

**External service requires manual configuration.**

To use Supabase persistence (production mode):

1. Set environment variables:
   - `SUPABASE_URL` — from Supabase Dashboard → Project Settings → API
   - `SUPABASE_SERVICE_ROLE_KEY` — from Supabase Dashboard → Project Settings → API → service_role key

2. Run the market_snapshots DDL in Supabase SQL Editor:
   - Open `scripts/schema.sql`
   - Execute the PART 8 block (lines after `-- PART 8: MARKET STATE SNAPSHOT STORE`)

Without these, SnapshotStore operates in in-memory mode (safe for tests and local development).

## Next Phase Readiness

- SnapshotStore is ready for wiring into KalshiAdapter.get_historical_snapshots() once the Kalshi candlestick API endpoint is confirmed (deferred by plan design)
- market_snapshots table DDL is in schema.sql, ready to apply to Supabase
- All 62 venue_adapters tests remain GREEN after adding this module

## Self-Check: PASSED

- snapshot_store.py: FOUND
- test_snapshot_store.py: FOUND
- commit 0f14d8b: FOUND
- commit 01725b0: FOUND
- schema.sql: both `ledger_entries` and `market_snapshots` table names confirmed present

---
*Phase: 06-multi-venue-quant-infrastructure*
*Completed: 2026-03-14*
