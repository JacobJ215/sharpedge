---
phase: 04-api-layer-front-ends
plan: "04"
subsystem: ui
tags: [react, nextjs, recharts, sse, streaming, tailwind, swr, vitest]

requires:
  - phase: 04-03
    provides: AlphaBadge, RegimeChip, api.ts (simulateBankroll, getValuePlays, ValuePlay type)

provides:
  - "Game detail page fetching /api/v1/games/{id}/analysis and rendering AnalysisPanel"
  - "Bankroll page with three-layer Recharts Monte Carlo fan chart (P5/P50/P95) and KellyCalculator"
  - "BettingCopilot chat page streaming SSE via ReadableStream POST (not EventSource)"
  - "Prediction markets dashboard filtering value-plays by sport=prediction_markets"
  - "AnalysisPanel component: win_probability, EV%, regime, alpha badge, key number grid"
  - "MonteCarloChart component: ComposedChart with band/expected/floor layers"
  - "KellyCalculator component: bankroll/win_rate/odds inputs with Kelly fraction output"
  - "ChatStream component: SSE streaming with progressive token append"
  - "PmTable component: platform/market/edge/alpha/badge/regime columns"

affects:
  - 04-05
  - 04-06
  - 04-07

tech-stack:
  added: []
  patterns:
    - "SSE streaming via fetch().body ReadableStream + getReader() — NOT EventSource (supports POST)"
    - "ResizeObserver jsdom polyfill in test-setup.ts for Recharts ResponsiveContainer"
    - "scrollIntoView typeof guard for jsdom test compatibility"
    - "ComposedChart (Area + Line) for multi-layer Monte Carlo fan chart"
    - "Async dynamic import in vitest tests to enable vi.stubGlobal fetch mocking before module load"

key-files:
  created:
    - apps/web/src/app/(dashboard)/games/[id]/page.tsx
    - apps/web/src/app/(dashboard)/bankroll/page.tsx
    - apps/web/src/app/(dashboard)/copilot/page.tsx
    - apps/web/src/app/(dashboard)/prediction-markets/page.tsx
    - apps/web/src/components/game/analysis-panel.tsx
    - apps/web/src/components/bankroll/monte-carlo-chart.tsx
    - apps/web/src/components/bankroll/kelly-calculator.tsx
    - apps/web/src/components/copilot/chat-stream.tsx
    - apps/web/src/components/prediction-markets/pm-table.tsx
    - apps/web/src/test/bankroll.test.tsx
    - apps/web/src/test/copilot.test.tsx
  modified:
    - apps/web/src/test-setup.ts

key-decisions:
  - "Recharts ComposedChart used over pure AreaChart for P5/P50/P95 because mixing Area (band) and Line (paths) types requires ComposedChart"
  - "scrollIntoView guarded with typeof check to avoid jsdom TypeError in tests"
  - "ResizeObserver polyfill added to test-setup.ts globally for all Recharts tests"
  - "Dynamic import in copilot tests enables vi.stubGlobal fetch mock to be set before module-level API_BASE reference"
  - "PmTable extracts platform from event string (Kalshi/Polymarket prefix detection) since ValuePlay has no explicit platform field"

patterns-established:
  - "SSE POST pattern: fetch + res.body.getReader() + decoder.decode() + split('\\n') on data: lines"
  - "Monte Carlo interpolation: scalar outcomes (p5/p50/p95) interpolated as linear paths for chart data array"

requirements-completed:
  - WEB-03
  - WEB-04
  - WEB-05
  - WEB-06

duration: 4min
completed: 2026-03-14
---

# Phase 4 Plan 04: Next.js Dashboard Pages (WEB-03 through WEB-06) Summary

**Four Next.js dashboard pages plus nine components completing game analysis, Monte Carlo bankroll fan chart (Recharts ComposedChart with P5/P50/P95 layers), SSE streaming copilot chat via ReadableStream POST, and alpha-ranked prediction markets table — 25 tests passing.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-03-14T06:34:17Z
- **Completed:** 2026-03-14T06:38:15Z
- **Tasks:** 2
- **Files modified:** 12 (11 created, 1 modified)

## Accomplishments

- Game detail page: useSWR fetches `/api/v1/games/{id}/analysis`, AnalysisPanel shows win probability, EV%, regime chip, alpha badge, key number proximity
- Bankroll page: KellyCalculator (Kelly fraction + stake output), MonteCarloChart (three-layer ComposedChart), SimulateForm triggers `simulateBankroll()`
- Copilot page: ChatStream streams SSE tokens progressively via ReadableStream POST, user/assistant bubble layout
- Prediction markets page: SWR with 60s refresh interval, PmTable with AlphaBadge + RegimeChip, regime legend dots

## Task Commits

1. **Task 1: Game detail page + Bankroll Monte Carlo page** - `b3178ca` (feat)
2. **Task 2: Copilot SSE chat page + Prediction markets page** - `0ddce60` (feat)

## Files Created/Modified

- `apps/web/src/app/(dashboard)/games/[id]/page.tsx` - Game detail page with useSWR + AnalysisPanel
- `apps/web/src/app/(dashboard)/bankroll/page.tsx` - KellyCalculator + SimulateForm + MonteCarloChart
- `apps/web/src/app/(dashboard)/copilot/page.tsx` - BettingCopilot page header + ChatStream
- `apps/web/src/app/(dashboard)/prediction-markets/page.tsx` - SWR-powered PmTable with regime legend
- `apps/web/src/components/game/analysis-panel.tsx` - Dense grid: win_prob / EV% / regime / alpha / key#
- `apps/web/src/components/bankroll/monte-carlo-chart.tsx` - Recharts ComposedChart three-layer fan chart
- `apps/web/src/components/bankroll/kelly-calculator.tsx` - Kelly fraction form with live stake output
- `apps/web/src/components/copilot/chat-stream.tsx` - SSE streaming chat UI (fetch POST + ReadableStream)
- `apps/web/src/components/prediction-markets/pm-table.tsx` - Platform/market/edge/alpha/regime table
- `apps/web/src/test/bankroll.test.tsx` - 6 tests for MonteCarloChart, KellyCalculator, AnalysisPanel
- `apps/web/src/test/copilot.test.tsx` - 7 tests for ChatStream SSE mocking and PmTable
- `apps/web/src/test-setup.ts` - ResizeObserver polyfill for jsdom

## Decisions Made

- Recharts `ComposedChart` used instead of `AreaChart` to mix `Area` band layers with `Line` path layers — `AreaChart` only accepts `Area` children
- `scrollIntoView` guarded with `typeof` check because jsdom doesn't implement it, causing test failures
- `ResizeObserver` polyfill added globally in `test-setup.ts` (Recharts `ResponsiveContainer` uses it on mount)
- Copilot test uses dynamic import (`await import(...)`) placed after `vi.stubGlobal('fetch', ...)` to ensure mock is active before the module-level `API_BASE` constant is evaluated
- `PmTable` derives platform name from `event` string prefix (Kalshi/Polymarket detection) since `ValuePlay` interface has no dedicated platform field

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] ResizeObserver polyfill for jsdom**
- **Found during:** Task 1 (MonteCarloChart tests)
- **Issue:** Recharts `ResponsiveContainer` calls `new ResizeObserver()` on mount; jsdom doesn't define it, causing `ReferenceError` in all three MonteCarloChart tests
- **Fix:** Added `globalThis.ResizeObserver` mock class in `test-setup.ts`
- **Files modified:** `apps/web/src/test-setup.ts`
- **Verification:** MonteCarloChart tests pass after fix
- **Committed in:** `b3178ca` (Task 1 commit)

**2. [Rule 1 - Bug] scrollIntoView TypeError in ChatStream tests**
- **Found during:** Task 2 (ChatStream render tests)
- **Issue:** jsdom `div.scrollIntoView is not a function` — thrown in `useEffect` hook, causing 4 tests to fail
- **Fix:** Added `typeof bottomRef.current.scrollIntoView === 'function'` guard before calling it
- **Files modified:** `apps/web/src/components/copilot/chat-stream.tsx`
- **Verification:** All 7 copilot tests pass after fix
- **Committed in:** `0ddce60` (Task 2 commit)

**3. [Rule 1 - Bug] AnalysisPanel EV% test regex matched multiple elements**
- **Found during:** Task 1 (AnalysisPanel test)
- **Issue:** `getByText(/8\.2|0\.082|ev/i)` matched both the label "EV%" and the value "8.2%" causing `TestingLibraryElementError: multiple elements found`
- **Fix:** Changed test regex to `/8\.2%/` which matches only the value cell
- **Files modified:** `apps/web/src/test/bankroll.test.tsx`
- **Verification:** AnalysisPanel test passes
- **Committed in:** `b3178ca` (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical polyfill, 2 bugs)
**Impact on plan:** All three fixes required for tests to pass in jsdom environment. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All four WEB-03 through WEB-06 pages complete with correct API endpoint wiring
- ChatStream SSE pattern established for mobile (Flutter) to mirror via http package + Stream
- MonteCarloChart accepts MonteCarloResult directly from `simulateBankroll()` — ready for bankroll route integration
- 25 total web tests passing (dashboard + value-plays + bankroll + copilot)

---
*Phase: 04-api-layer-front-ends*
*Completed: 2026-03-14*
