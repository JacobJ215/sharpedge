---
phase: 10-training-pipeline-validation
plan: 02
subsystem: training-pipeline
tags: [supabase, kalshi, polymarket, upsert, preflight, volume-filter, prediction-markets]

# Dependency graph
requires:
  - phase: 10-training-pipeline-validation
    plan: 01
    provides: resolved_pm_markets DDL migration + Wave 0 RED tests for Supabase upsert, preflight, volume filter, and Supabase SELECT
provides:
  - download_pm_historical.py with Supabase upsert path, Kalshi preflight auth check, and Polymarket volume filter
  - process_pm_historical.py with Supabase SELECT path in main() replacing parquet read
affects:
  - 10-03 (train_pm_models.py — reads processed per-category data from Supabase or parquet)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-mode pattern: check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY; live path upserts to Supabase; offline path writes parquet for test compatibility"
    - "Kalshi preflight: await get_markets(limit=1) before pagination loop; sys.exit with actionable error on exception"
    - "Polymarket volume filter: exclude markets with volume <= 100 before row construction and upsert"
    - "process_pm_historical.py uses sharpedge_db.client.get_supabase_client() so test mocks via sharpedge_db.client namespace work correctly"

key-files:
  created: []
  modified:
    - scripts/download_pm_historical.py
    - scripts/process_pm_historical.py

key-decisions:
  - "Preflight fires inside backfill_kalshi_resolved async function as an await call — not a separate sync wrapper — avoids event loop nesting in async context"
  - "process_pm_historical uses sharpedge_db.client.get_supabase_client (not an inline create_client) so Wave 0 test mock at sharpedge_db.client namespace takes effect"
  - "Offline/fixture path writes parquet as before — parquet-path tests remain green without modification"

requirements-completed: [TRAIN-01, TRAIN-02]

# Metrics
duration: 5min
completed: 2026-03-16
---

# Phase 10 Plan 02: Supabase Upsert + Preflight + Volume Filter Summary

**Migrated download_pm_historical.py from parquet-write to Supabase-upsert with Kalshi preflight auth check and Polymarket volume filter; migrated process_pm_historical.py from parquet-read to Supabase SELECT — all 24 scripts unit tests pass**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-16T01:54:01Z
- **Completed:** 2026-03-16T01:58:24Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Modified `scripts/download_pm_historical.py`:
  - Added `sys` import
  - Added `_get_supabase_client()` helper (checks SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)
  - Added `_detect_category()` mapping Kalshi event_ticker prefix (KXPO, KXFE, KXBT, KXEN, KXWT) to category name
  - Added `_build_kalshi_row()` building canonical resolved_pm_markets row dict from KalshiMarket object
  - Added `_build_polymarket_row()` building canonical resolved_pm_markets row dict from PolymarketMarket + resolved_yes
  - Added Kalshi preflight check in `backfill_kalshi_resolved`: `await client.get_markets(limit=1)` before pagination loop; `sys.exit` with actionable message on exception
  - Added Supabase upsert path in `backfill_kalshi_resolved`: calls `table("resolved_pm_markets").upsert(row, on_conflict="market_id,source").execute()` per row
  - Added Polymarket volume filter in `backfill_polymarket_resolved`: `[m for m in all_markets if getattr(m, "volume", 0) > 100]` before row construction
  - Added Supabase upsert path in `backfill_polymarket_resolved`
  - Offline/fixture path unchanged; parquet write preserved as fallback when Supabase not configured

- Modified `scripts/process_pm_historical.py`:
  - Added `os` import
  - Added `_get_resolved_pm_from_supabase()`: checks SUPABASE_URL+SUPABASE_SERVICE_ROLE_KEY, calls `sharpedge_db.client.get_supabase_client()`, SELECT * FROM resolved_pm_markets, returns [] on any error
  - Added `_process_supabase_df()`: iterates Supabase-sourced DataFrame, builds feature rows via existing helpers, calls `_write_categories()`
  - Modified `main()`: checks `os.environ.get("SUPABASE_URL")` first; if set, calls Supabase path; else falls through to existing parquet-reading logic unchanged

## Task Commits

1. **Task 1: Migrate download_pm_historical.py** - `a0945ee` (feat) — preflight + upsert + volume filter; 16/16 tests pass
2. **Task 2: Migrate process_pm_historical.py** - `990535d` (feat) — Supabase SELECT path in main(); 24/24 tests pass

## Files Created/Modified

- `scripts/download_pm_historical.py` — +sys import, +_get_supabase_client(), +_detect_category(), +_build_kalshi_row(), +_build_polymarket_row(), preflight in backfill_kalshi_resolved, upsert paths in both backfill functions, volume filter in backfill_polymarket_resolved
- `scripts/process_pm_historical.py` — +os import, +_get_resolved_pm_from_supabase(), +_process_supabase_df(), modified main() to check SUPABASE_URL

## Decisions Made

- Preflight implemented as an `await` call inside `backfill_kalshi_resolved` (not a standalone sync function) to avoid event-loop nesting in the async context
- `_get_resolved_pm_from_supabase()` calls `sharpedge_db.client.get_supabase_client()` via module attribute access rather than a local import so that test patches at `sharpedge_db.client.get_supabase_client` take effect as expected
- Offline/parquet path preserved unchanged in both scripts — test compatibility maintained without any test file edits

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: scripts/download_pm_historical.py (contains sys.exit preflight guard)
- FOUND: scripts/process_pm_historical.py (contains resolved_pm_markets Supabase SELECT)
- FOUND commit a0945ee (feat: download_pm_historical.py migration)
- FOUND commit 990535d (feat: process_pm_historical.py migration)
- All 24 tests in tests/unit/scripts/ pass

---
*Phase: 10-training-pipeline-validation*
*Completed: 2026-03-16*
