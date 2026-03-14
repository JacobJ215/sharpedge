---
phase: 04-api-layer-front-ends
plan: "03"
subsystem: ui
tags: [nextjs, react, swr, recharts, tailwind, vitest, testing-library, supabase]

# Dependency graph
requires:
  - phase: 04-api-layer-front-ends
    provides: FastAPI /api/v1/value-plays and /api/v1/users/{id}/portfolio endpoints
provides:
  - Typed fetch wrappers for all /api/v1/* endpoints (getValuePlays, getPortfolio, simulateBankroll)
  - Supabase browser client singleton
  - Dashboard layout with dark zinc-950 trading-terminal nav
  - Portfolio overview page (WEB-01) with StatsCards + RoiCurve + active bets table
  - Value plays page (WEB-02) with dense PlaysTable, auto-refresh every 60s
  - AlphaBadge colored pill component (PREMIUM/HIGH/MEDIUM/SPECULATIVE)
  - RegimeChip monospace chip component
  - 12 passing component tests (vitest + testing-library)
affects: [04-04, 04-05, 04-06, 04-07, 04-08]

# Tech tracking
tech-stack:
  added: [swr@2.2.5, recharts@2.12.7, clsx@2.1.1, @supabase/supabase-js@2.45.0]
  patterns:
    - SWR data fetching with typed API wrappers
    - TDD Red-Green cycle with vitest + testing-library
    - Dense HTML tables over card-heavy UI for trading terminal aesthetic
    - Tailwind color tokens for badge states (emerald/blue/amber/zinc)

key-files:
  created:
    - apps/web/src/lib/api.ts
    - apps/web/src/lib/supabase.ts
    - apps/web/src/app/(dashboard)/layout.tsx
    - apps/web/src/app/(dashboard)/page.tsx
    - apps/web/src/app/(dashboard)/value-plays/page.tsx
    - apps/web/src/components/ui/alpha-badge.tsx
    - apps/web/src/components/value-plays/regime-chip.tsx
    - apps/web/src/components/value-plays/plays-table.tsx
    - apps/web/src/components/portfolio/stats-cards.tsx
    - apps/web/src/components/portfolio/roi-curve.tsx
    - apps/web/src/test/dashboard.test.tsx
    - apps/web/src/test/value-plays.test.tsx
  modified: []

key-decisions:
  - "Dense HTML table used over shadcn DataTable for trading-terminal feel — fewer abstractions, more compact row density"
  - "Portfolio page defers real auth token to WEB-05 — uses empty string placeholder with SWR key ['portfolio', userId] to avoid build-time errors"
  - "RoiCurve uses static placeholder data array — real ROI history endpoint deferred to later plan"
  - "PlaysTable sort defaults to ascending on first click of a new column, toggles on subsequent clicks"

patterns-established:
  - "SWR Pattern: useSWR(key, fetcher, { refreshInterval }) with named key tuples for cache invalidation"
  - "Badge Pattern: AlphaBadge receives badge prop, maps to Tailwind color tokens via Record<Badge, string>"
  - "Table Pattern: native HTML table with Tailwind classes (border-zinc-800, hover:bg-zinc-900/40, font-mono numbers)"
  - "Loading Pattern: animate-pulse skeleton divs mirror final layout dimensions"

requirements-completed: [WEB-01, WEB-02]

# Metrics
duration: 3min
completed: 2026-03-14
---

# Phase 4 Plan 03: API Client + Dashboard Pages Summary

**Next.js 14 API client layer (api.ts + supabase.ts) plus portfolio overview (WEB-01) and value plays (WEB-02) pages with dense trading-terminal UI, SWR data fetching, AlphaBadge/RegimeChip components, and 12 passing vitest tests**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-14T06:28:19Z
- **Completed:** 2026-03-14T06:31:30Z
- **Tasks:** 2
- **Files modified:** 12 created

## Accomplishments

- Typed API client (api.ts) with getValuePlays(), getPortfolio(), simulateBankroll() — all using URLSearchParams query building and auth header injection
- Portfolio page with SWR refresh, StatsCards 4-metric grid, Recharts AreaChart ROI curve, active bets table
- Value plays page with 60s auto-refresh via SWR refreshInterval, live pulse indicator, dense PlaysTable with sortable alpha_score column
- AlphaBadge colored pill and RegimeChip monospace chip components tested and passing
- 12 component tests pass across dashboard.test.tsx and value-plays.test.tsx

## Task Commits

1. **Task 1: API client, Supabase client, dashboard layout, AlphaBadge, RegimeChip** - `2644127` (feat)
2. **Task 2: Portfolio overview page, value plays page, PlaysTable, StatsCards, RoiCurve** - `57cca8f` (feat)

## Files Created/Modified

- `apps/web/src/lib/api.ts` - Typed fetch wrappers: getValuePlays, getPortfolio, simulateBankroll
- `apps/web/src/lib/supabase.ts` - createClient singleton for browser use
- `apps/web/src/app/(dashboard)/layout.tsx` - Dark nav with 5 links, zinc-950 bg
- `apps/web/src/app/(dashboard)/page.tsx` - Portfolio overview page (WEB-01)
- `apps/web/src/app/(dashboard)/value-plays/page.tsx` - Value plays page (WEB-02) with 60s refresh
- `apps/web/src/components/ui/alpha-badge.tsx` - Colored pill badge for PREMIUM/HIGH/MEDIUM/SPECULATIVE
- `apps/web/src/components/value-plays/regime-chip.tsx` - Monospace regime state chip
- `apps/web/src/components/value-plays/plays-table.tsx` - Dense sortable HTML table
- `apps/web/src/components/portfolio/stats-cards.tsx` - 4-metric stat grid (ROI/Win Rate/CLV/Drawdown)
- `apps/web/src/components/portfolio/roi-curve.tsx` - Recharts AreaChart with emerald gradient
- `apps/web/src/test/dashboard.test.tsx` - 6 tests: AlphaBadge + RegimeChip rendering and styling
- `apps/web/src/test/value-plays.test.tsx` - 6 tests: PlaysTable rows, badges, chips, headers, sort

## Decisions Made

- Dense HTML table used over shadcn DataTable — fewer abstractions, tighter row density matches trading-terminal aesthetic
- Portfolio page uses empty string auth token placeholder — real auth integration deferred to WEB-05
- PlaysTable sort toggles asc/desc on same column, resets to asc when switching columns
- RoiCurve accepts static data prop — real ROI history fetching deferred to a later plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Supabase env vars (NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY) and NEXT_PUBLIC_API_URL are read from environment at runtime.

## Next Phase Readiness

- api.ts, layout, and shared components are ready for WEB-03 through WEB-06 to extend
- PlaysTable, StatsCards, AlphaBadge, RegimeChip are importable by any subsequent dashboard page
- SWR pattern established for all future data fetching pages
- Auth token integration needed before portfolio page fetches real data

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*

## Self-Check: PASSED

- FOUND: apps/web/src/lib/api.ts
- FOUND: apps/web/src/lib/supabase.ts
- FOUND: apps/web/src/app/(dashboard)/page.tsx
- FOUND: apps/web/src/app/(dashboard)/value-plays/page.tsx
- FOUND: apps/web/src/components/value-plays/plays-table.tsx
- FOUND commit: 2644127 (Task 1)
- FOUND commit: 57cca8f (Task 2)
