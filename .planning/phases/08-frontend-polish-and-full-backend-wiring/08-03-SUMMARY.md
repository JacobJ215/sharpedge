---
phase: 08-frontend-polish-and-full-backend-wiring
plan: "03"
subsystem: web-dashboard
tags: [wire-02, widgets, venue-dislocation, exposure, react, next-js]
dependency_graph:
  requires: [08-02]
  provides: [VenueDislocWidget, ExposureWidget, prediction-markets-wired, bankroll-wired]
  affects: [apps/web/src/app/(dashboard)/prediction-markets/page.tsx, apps/web/src/app/(dashboard)/bankroll/page.tsx]
tech_stack:
  added: []
  patterns: [plain-fetch, use-client, useState-useEffect, zinc-palette]
key_files:
  created:
    - apps/web/components/venue-dislocation/venue-disloc-widget.tsx
    - apps/web/components/exposure/exposure-widget.tsx
    - apps/web/src/components/venue-dislocation/venue-disloc-widget.tsx
    - apps/web/src/components/exposure/exposure-widget.tsx
    - apps/web/src/components/venue/VenueDislocWidget.tsx
    - apps/web/src/components/venue/ExposureWidget.tsx
  modified:
    - apps/web/src/app/(dashboard)/prediction-markets/page.tsx
    - apps/web/src/app/(dashboard)/bankroll/page.tsx
decisions:
  - Components created at both test-expected path (apps/web/components/) and src path (apps/web/src/components/venue/) with re-export stubs to satisfy both the test's fs.existsSync checks and the page's @-alias imports
  - Pre-existing build failure in roi-curve.tsx (recharts defs export) documented as deferred — unrelated to this plan's changes
metrics:
  duration: "205 seconds (~3.5 minutes)"
  completed_date: "2026-03-15"
  tasks_completed: 2
  files_created: 6
  files_modified: 2
---

# Phase 08 Plan 03: VenueDislocWidget + ExposureWidget Summary

**One-liner:** Two 'use client' React widgets wired into /markets and /bankroll dashboard pages — VenueDislocWidget shows cross-venue dislocation bps table with color coding; ExposureWidget shows per-venue Kelly utilization progress bars.

---

## What Was Built

### Task 1: VenueDislocWidget + prediction markets page

`apps/web/components/venue-dislocation/venue-disloc-widget.tsx` — new `'use client'` component:
- Props: `{ marketId: string }` — returns null when marketId is empty
- Fetches `GET /api/v1/markets/dislocation?market_id={marketId}` with no auth header (public endpoint)
- Loading state: animated skeleton divs
- Error state: "Dislocation data unavailable" in `text-zinc-500`
- Empty scores: "No dislocation data for this market"
- Success: "Consensus: X.X%" header stat + table with Venue / Mid Prob / Disloc (bps) / Stale columns
- Disloc column color: `text-green-400` for bps > 5, `text-red-400` for bps < -5, `text-zinc-400` for ~0
- Stale venues show `(stale)` suffix in `text-zinc-600`

`apps/web/src/app/(dashboard)/prediction-markets/page.tsx` — extended:
- Added `VenueDislocWidget` import at top
- Added "Cross-Venue Dislocation" section at bottom using first play's market_id or static fallback `KXBTCD-01`
- All existing PM edge table content preserved

### Task 2: ExposureWidget + bankroll page

`apps/web/components/exposure/exposure-widget.tsx` — new `'use client'` component:
- No props — fetches `GET /api/v1/bankroll/exposure` (public in-memory endpoint)
- Loading/error/empty states follow same pattern as VenueDislocWidget
- Success: "Total Exposure: $X / Bankroll: $Y" header + per-venue rows with progress bars
- Progress bar: `bg-amber-500` for utilization_pct > 50, `bg-green-600` for ≤ 50
- Overall utilization summary row at bottom
- Clamps progress bar width to 100% via `Math.min(utilization_pct, 100)`

`apps/web/src/app/(dashboard)/bankroll/page.tsx` — extended:
- Added `ExposureWidget` import at top
- Added "Live Exposure (Current Session)" section below Monte Carlo chart
- Added "(Resets on server restart — reflects current process positions)" note
- Monte Carlo chart, Kelly calculator, and Exposure Limits section all preserved

---

## Test Results

```
 ✓ src/test/venue-dislocation.test.tsx (2 tests) 3ms
 ✓ src/test/exposure-widget.test.tsx (2 tests) 4ms

 Test Files  2 passed (2)
      Tests  4 passed (4)
```

All 4 WIRE-02 tests GREEN.

---

## Deviations from Plan

### Path deviation: test-expected vs plan-specified component paths

**Found during:** Task 1 (RED phase)
**Issue:** The pre-written RED stubs (`venue-dislocation.test.tsx`, `exposure-widget.test.tsx`) resolve component paths via `path.join(__dirname, '../../...')` from `src/test/`, which resolves to `apps/web/components/` (without `src/`), not `apps/web/src/components/venue/` as specified in the plan frontmatter.
**Fix:** Created actual component implementations at the test-expected paths (`apps/web/components/venue-dislocation/` and `apps/web/components/exposure/`). Added thin re-export files at `apps/web/src/components/venue/VenueDislocWidget.tsx` and `ExposureWidget.tsx` so the dashboard pages can import via the `@` alias. Both test checks and page imports satisfied.
**Files added:** 6 (4 components + 2 re-export stubs)
**Rule applied:** Rule 1 (Auto-fix) — component paths are a correctness requirement for tests to pass

### Pre-existing build failure (deferred)

`apps/web/src/components/portfolio/roi-curve.tsx` has a TypeScript error: `Module '"recharts"' has no exported member 'defs'`. This failure existed before this plan's changes (confirmed by `git stash` verification). This is out-of-scope per deviation scope boundary rules. Logged to deferred items.

---

## Commits

| Hash | Message |
|------|---------|
| f8db12b | feat(08-03): VenueDislocWidget + ExposureWidget — WIRE-02 web dashboard widgets |

---

## Self-Check

Files created:
- apps/web/components/venue-dislocation/venue-disloc-widget.tsx: FOUND
- apps/web/components/exposure/exposure-widget.tsx: FOUND
- apps/web/src/components/venue/VenueDislocWidget.tsx: FOUND
- apps/web/src/components/venue/ExposureWidget.tsx: FOUND

Commit f8db12b: FOUND

## Self-Check: PASSED
