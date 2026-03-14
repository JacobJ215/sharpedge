---
phase: 06-multi-venue-quant-infrastructure
plan: 07
subsystem: api
tags: [langchain, copilot, venue-adapters, dislocation, exposure, kalshi, polymarket]

# Dependency graph
requires:
  - phase: 06-06
    provides: ExposureBook, score_dislocation, KalshiAdapter, PolymarketAdapter — all Phase 6 infrastructure this plan surfaces through the copilot

provides:
  - venue_tools.py with get_venue_dislocation and get_exposure_status copilot tools
  - COPILOT_TOOLS extended to 12 tools (was 10)
  - First real consumer of normalization.py CanonicalQuote construction path

affects:
  - BettingCopilot agent (auto-picks up new tools via COPILOT_TOOLS)
  - Mobile/web copilot consumers querying dislocation or exposure

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Separate venue_tools.py module to respect 500-line limit on tools.py
    - Module-level singleton (_EXPOSURE_BOOK) for in-process session persistence
    - _run_async() bridge for calling async adapters from sync @tool functions
    - VENUE_TOOLS list exported for list-concatenation into COPILOT_TOOLS

key-files:
  created:
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/venue_tools.py
  modified:
    - packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py

key-decisions:
  - "venue_tools.py as separate file: tools.py was 447 lines; adding 2 tools would exceed 500-line limit"
  - "COPILOT_TOOLS extended via list concatenation (+ VENUE_TOOLS): clean, backward-compatible; agent.py unchanged"
  - "_EXPOSURE_BOOK singleton initialized lazily from SHARPEDGE_BANKROLL env var (default 10000.0): consistent with trading session semantics"
  - "CanonicalQuote constructed directly from CanonicalMarket fields: first real consumer of normalization path, closes wiring gap from 06-02"

patterns-established:
  - "New copilot tool groups go in separate *_tools.py files, exported as *_TOOLS list, concatenated into COPILOT_TOOLS"
  - "Async adapter calls bridged to sync @tool via _run_async() with event loop detection"

requirements-completed: [DISLO-01, RISK-01]

# Metrics
duration: 5min
completed: 2026-03-14
---

# Phase 6 Plan 07: BettingCopilot Venue Tools Summary

**Two new copilot tools — get_venue_dislocation and get_exposure_status — surface Phase 6 dislocation detection and exposure book state through the existing LangGraph agent interface**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T16:39:20Z
- **Completed:** 2026-03-14T16:44:00Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 extended)

## Accomplishments
- Created venue_tools.py (198 lines) with 2 Phase 6 infrastructure tools
- get_venue_dislocation: fetches quotes from KalshiAdapter/PolymarketAdapter, constructs CanonicalQuote objects, calls score_dislocation(); graceful offline error dict when adapters unavailable
- get_exposure_status: reads module-level ExposureBook singleton, returns per-venue exposure, utilization %, and concentration cap headroom
- COPILOT_TOOLS extended from 10 to 12 tools; tools.py stays at 449 lines (under 500-line limit)
- BettingCopilot agent auto-picks up new tools — no change to agent.py needed

## Task Commits

Each task was committed atomically:

1. **Task 1: venue_tools.py — get_venue_dislocation and get_exposure_status copilot tools** - `45d1851` (feat)
2. **Task 2: Extend COPILOT_TOOLS in tools.py with VENUE_TOOLS** - `c50cba7` (feat)

**Plan metadata:** see final commit (docs: complete plan)

## Files Created/Modified
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/venue_tools.py` - 2 venue copilot tools + VENUE_TOOLS list; 198 lines
- `packages/agent_pipeline/src/sharpedge_agent_pipeline/copilot/tools.py` - added VENUE_TOOLS import + list concatenation; 449 lines

## Decisions Made
- venue_tools.py as separate file: tools.py was 447 lines; adding 2 more would cross 500-line limit
- COPILOT_TOOLS extended via `+ VENUE_TOOLS` list concatenation: clean, backward-compatible, agent.py unchanged
- ExposureBook singleton lazily initialized from `SHARPEDGE_BANKROLL` env var (default 10000.0): in-process session persistence
- CanonicalQuote constructed from CanonicalMarket fields (yes_bid, yes_ask → mid/spread): first real consumer of normalization.py CanonicalQuote type, closes wiring gap from Phase 06-02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required. Tools degrade gracefully to `{"error": ...}` when adapters are offline (no API keys).

## Self-Check: PASSED

- [x] venue_tools.py exists: FOUND
- [x] VENUE_TOOLS contains 2 tools ('get_venue_dislocation', 'get_exposure_status')
- [x] COPILOT_TOOLS contains 12 tools total
- [x] tools.py is 449 lines (under 500)
- [x] venue_tools.py is 198 lines (under 200)
- [x] Commits 45d1851 and c50cba7 exist in git log

## Next Phase Readiness
- Phase 6 complete: all 7 plans delivered (venue adapters, market lifecycle, normalization, microstructure, dislocation, exposure/risk, settlement ledger, copilot wiring)
- BettingCopilot now surfaces all Phase 6 intelligence through 12 tools

---
*Phase: 06-multi-venue-quant-infrastructure*
*Completed: 2026-03-14*
